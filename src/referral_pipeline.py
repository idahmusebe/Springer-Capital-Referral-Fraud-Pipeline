from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"


# ============================================================
# LOAD SOURCE DATA
# ============================================================

def load_data():
    """
    Load all seven source CSV files into Pandas DataFrames.
    """

    tables = {
        "lead_logs": "lead_log.csv",
        "paid_transactions": "paid_transactions.csv",
        "referral_rewards": "referral_rewards.csv",
        "user_logs": "user_logs.csv",
        "user_referral_logs": "user_referral_logs.csv",
        "user_referral_statuses": "user_referral_statuses.csv",
        "user_referrals": "user_referrals.csv",
    }

    data = {}

    for table_name, file_name in tables.items():
        file_path = DATA_DIR / file_name
        data[table_name] = pd.read_csv(file_path)

    print("All source tables loaded successfully!")

    for table_name, dataframe in data.items():
        print(f"{table_name}: {len(dataframe)} rows")

    return data


# ============================================================
# DATA CLEANING
# ============================================================

def clean_data(data):
    """
    Clean source data and standardize data types.
    """

    datetime_columns = {
        "lead_logs": ["created_at"],
        "paid_transactions": ["transaction_at"],
        "referral_rewards": ["created_at"],
        "user_logs": ["membership_expired_date"],
        "user_referral_logs": ["created_at"],
        "user_referral_statuses": ["created_at"],
        "user_referrals": ["referral_at", "updated_at"],
    }

    # Convert timestamp columns to UTC-aware datetime.
    for table_name, columns in datetime_columns.items():

        for column in columns:

            if column in data[table_name].columns:

                data[table_name][column] = pd.to_datetime(
                    data[table_name][column],
                    errors="coerce",
                    utc=True,
                )

    # Remove unnecessary whitespace from text values.
    for dataframe in data.values():

        for column in dataframe.select_dtypes(
            include=["object"]
        ).columns:

            dataframe[column] = dataframe[column].apply(
                lambda value:
                    value.strip()
                    if isinstance(value, str)
                    else value
            )

    # Reward values must be numeric.
    data["referral_rewards"]["reward_value"] = pd.to_numeric(
        data["referral_rewards"]["reward_value"],
        errors="coerce",
    )

    print("Source tables cleaned successfully!")

    return data


# ============================================================
# TIMEZONE CONVERSION
# ============================================================

def convert_to_local_time(timestamp, timezone_name):
    """
    Convert a UTC timestamp into the supplied local timezone.
    """

    if pd.isna(timestamp):
        return timestamp

    if pd.isna(timezone_name):
        return timestamp

    try:
        return timestamp.tz_convert(
            ZoneInfo(str(timezone_name))
        )

    except Exception:
        return timestamp


def convert_timestamps(referral_dataset):
    """
    Convert timestamps to the appropriate local timezone.

    Transaction timestamps use the transaction timezone.

    Referral timestamps do not contain a timezone in the
    user_referrals table, so the referrer's home-club timezone
    is used as the available related timezone.
    """

    # Transaction timestamp.
    referral_dataset["transaction_at"] = referral_dataset.apply(
        lambda row: convert_to_local_time(
            row["transaction_at"],
            row["timezone_transaction"],
        ),
        axis=1,
    )

    # Referral timestamps.
    for column in [
        "referral_at",
        "updated_at",
        "referrer_membership_expired_date",
    ]:

        referral_dataset[column] = referral_dataset.apply(
            lambda row: convert_to_local_time(
                row[column],
                row["referrer_timezone_homeclub"],
            ),
            axis=1,
        )

    print("Timestamp conversion completed")

    return referral_dataset


# ============================================================
# BUILD REFERRAL DATASET
# ============================================================

def build_referral_dataset(data):
    """
    Join the source tables into the referral-level dataset.
    """

    user_referrals = data["user_referrals"].copy()
    statuses = data["user_referral_statuses"].copy()
    rewards = data["referral_rewards"].copy()
    transactions = data["paid_transactions"].copy()
    users = data["user_logs"].copy()
    lead_logs = data["lead_logs"].copy()

    # --------------------------------------------------------
    # Join referral statuses
    # --------------------------------------------------------

    user_referrals = user_referrals.merge(
        statuses[
            ["id", "description"]
        ],
        how="left",
        left_on="user_referral_status_id",
        right_on="id",
    )

    user_referrals = user_referrals.rename(
        columns={
            "description": "referral_status"
        }
    )

    user_referrals = user_referrals.drop(
        columns=["id"],
        errors="ignore",
    )

    # --------------------------------------------------------
    # Join referral rewards
    # --------------------------------------------------------

    user_referrals = user_referrals.merge(
        rewards[
            ["id", "reward_value", "reward_type"]
        ],
        how="left",
        left_on="referral_reward_id",
        right_on="id",
    )

    user_referrals = user_referrals.drop(
        columns=["id"],
        errors="ignore",
    )

    # --------------------------------------------------------
    # Join paid transactions
    # --------------------------------------------------------

    user_referrals = user_referrals.merge(
        transactions[
            [
                "transaction_id",
                "transaction_status",
                "transaction_at",
                "transaction_location",
                "timezone_transaction",
                "transaction_type",
            ]
        ],
        how="left",
        on="transaction_id",
    )

    # --------------------------------------------------------
    # Join referrer user information
    # --------------------------------------------------------

    # user_logs may contain multiple records for one user.
    # Keep the latest log record to prevent duplicate referrals.
    users = users.sort_values("id")

    users_latest = users.drop_duplicates(
        subset=["user_id"],
        keep="last",
    )

    users_latest = users_latest.rename(
        columns={
            "name": "referrer_name",
            "phone_number": "referrer_phone_number",
            "homeclub": "referrer_homeclub",
            "timezone_homeclub": "referrer_timezone_homeclub",
            "membership_expired_date":
                "referrer_membership_expired_date",
            "is_deleted": "referrer_is_deleted",
        }
    )

    user_columns = [
        "user_id",
        "referrer_name",
        "referrer_phone_number",
        "referrer_homeclub",
        "referrer_timezone_homeclub",
        "referrer_membership_expired_date",
        "referrer_is_deleted",
    ]

    user_referrals = user_referrals.merge(
        users_latest[user_columns],
        how="left",
        left_on="referrer_id",
        right_on="user_id",
    )

    user_referrals = user_referrals.drop(
        columns=["user_id"],
        errors="ignore",
    )

    # --------------------------------------------------------
    # Join lead information
    # --------------------------------------------------------

    lead_logs = lead_logs.sort_values("created_at")

    lead_latest = lead_logs.drop_duplicates(
        subset=["lead_id"],
        keep="last",
    )

    lead_latest = lead_latest[
        [
            "lead_id",
            "source_category",
            "timezone_location",
        ]
    ].rename(
        columns={
            "source_category":
                "lead_source_category",
            "timezone_location":
                "lead_timezone",
        }
    )

    user_referrals = user_referrals.merge(
        lead_latest,
        how="left",
        left_on="referee_id",
        right_on="lead_id",
    )

    user_referrals = user_referrals.drop(
        columns=["lead_id"],
        errors="ignore",
    )

    # --------------------------------------------------------
    # Referral source category
    # --------------------------------------------------------

    user_referrals["referral_source_category"] = (
        user_referrals["referral_source"]
        .map(
            {
                "User Sign Up": "Online",
                "Draft Transaction": "Offline",
            }
        )
    )

    lead_mask = user_referrals[
        "referral_source"
    ].eq("Lead")

    user_referrals.loc[
        lead_mask,
        "referral_source_category"
    ] = user_referrals.loc[
        lead_mask,
        "lead_source_category"
    ]

    # --------------------------------------------------------
    # Reward granted information
    # --------------------------------------------------------
    #
    # The supplied user_referral_logs table contains:
    #   - id
    #   - user_referral_id
    #   - source_transaction_id
    #   - created_at
    #   - is_reward_granted
    #
    # However, the supplied user_referral_id values do not
    # match the referral_id values in user_referrals.
    #
    # Also, the source_transaction_id values for the 17
    # reward-granted records do not match paid_transactions.
    #
    # Therefore, we cannot safely assign a reward-granted
    # timestamp to a particular referral without inventing
    # a relationship that is not supported by the data.
    #
    # This source-data limitation is documented in the README.
    # --------------------------------------------------------

    user_referrals["reward_granted_at"] = pd.NaT

    # --------------------------------------------------------
    # Remove duplicate referrals
    # --------------------------------------------------------

    duplicate_count = user_referrals.duplicated(
        subset=["referral_id"]
    ).sum()

    print(
        f"Duplicate referral records after joins: "
        f"{duplicate_count}"
    )

    user_referrals = user_referrals.drop_duplicates(
        subset=["referral_id"],
        keep="first",
    )

    print(
        f"Referral rows: {len(user_referrals)}"
    )

    return user_referrals


# ============================================================
# BUSINESS LOGIC
# ============================================================

def apply_business_logic(referral_dataset):
    """
    Apply the referral validation rules supplied in the test.
    """

    # --------------------------------------------------------
    # Condition 1: Successful referral reward
    # --------------------------------------------------------

    reward_value_valid = (
        pd.to_numeric(
            referral_dataset["reward_value"],
            errors="coerce",
        )
        .fillna(0)
        .gt(0)
    )

    status_successful = (
        referral_dataset["referral_status"]
        .eq("Berhasil")
    )

    transaction_exists = (
        referral_dataset["transaction_id"]
        .notna()
    )

    transaction_paid = (
        referral_dataset["transaction_status"]
        .fillna("")
        .astype(str)
        .str.upper()
        .eq("PAID")
    )

    transaction_new = (
        referral_dataset["transaction_type"]
        .fillna("")
        .astype(str)
        .str.upper()
        .eq("NEW")
    )

    transaction_at = pd.to_datetime(
        referral_dataset["transaction_at"],
        errors="coerce",
        utc=True,
    )

    referral_at = pd.to_datetime(
        referral_dataset["referral_at"],
        errors="coerce",
        utc=True,
    )

    transaction_after_referral = (
        transaction_at.notna()
        & referral_at.notna()
        & (
            transaction_at
            > referral_at
        )
    )

    transaction_same_month = (
        transaction_at.notna()
        & referral_at.notna()
        & (
            transaction_at.dt.year
            == referral_at.dt.year
        )
        & (
            transaction_at.dt.month
            == referral_at.dt.month
        )
    )

    membership_valid = (
        referral_dataset[
            "referrer_membership_expired_date"
        ].isna()
        |
        (
            referral_dataset[
                "referrer_membership_expired_date"
            ]
            >= referral_dataset["referral_at"]
        )
    )

    account_valid = (
        referral_dataset[
            "referrer_is_deleted"
        ]
        .astype("boolean")
        .fillna(False)
        .eq(False)
    )

    reward_granted = (
        referral_dataset[
            "reward_granted_at"
        ].notna()
    )

    valid_condition_1 = (
        reward_value_valid
        & status_successful
        & transaction_exists
        & transaction_paid
        & transaction_new
        & transaction_after_referral
        & transaction_same_month
        & membership_valid
        & account_valid
        & reward_granted
    )

    # --------------------------------------------------------
    # Condition 2: Pending or failed with no reward
    # --------------------------------------------------------

    pending_or_failed = (
        referral_dataset["referral_status"]
        .isin(
            [
                "Menunggu",
                "Tidak Berhasil",
            ]
        )
    )

    no_reward_assigned = (
        referral_dataset["reward_value"].isna()
        |
        (
            pd.to_numeric(
                referral_dataset["reward_value"],
                errors="coerce",
            )
            == 0
        )
    )

    valid_condition_2 = (
        pending_or_failed
        & no_reward_assigned
    )

    # --------------------------------------------------------
    # Final validation flag
    # --------------------------------------------------------

    referral_dataset[
        "is_business_logic_valid"
    ] = (
        valid_condition_1
        | valid_condition_2
    ).astype(bool)

    print(
        "Business logic applied successfully!"
    )

    print(
        "\nBusiness logic results:"
    )

    print(
        referral_dataset[
            "is_business_logic_valid"
        ].value_counts()
    )

    return referral_dataset


# ============================================================
# FINAL OUTPUT
# ============================================================

def prepare_final_output(referral_dataset):
    """
    Select the required report columns and handle missing
    values without inventing factual data.
    """

    referral_dataset = referral_dataset.reset_index(
        drop=True
    )

    # --------------------------------------------------------
    # Referral details ID
    # --------------------------------------------------------
    #
    # The source log ID cannot be reliably connected to the
    # 46 referral records because the supplied foreign-key
    # values do not match the referral IDs.
    #
    # A sequential report-level ID is therefore generated.
    # --------------------------------------------------------

    referral_dataset.insert(
        0,
        "referral_details_id",
        range(
            1,
            len(referral_dataset) + 1,
        ),
    )

    # --------------------------------------------------------
    # Reward days
    # --------------------------------------------------------

    referral_dataset[
        "num_reward_days"
    ] = (
        pd.to_numeric(
            referral_dataset["reward_value"],
            errors="coerce",
        )
        .fillna(0)
        .astype(int)
    )

    # --------------------------------------------------------
    # Required final columns
    # --------------------------------------------------------

    final_columns = [
        "referral_details_id",
        "referral_id",
        "referral_source",
        "referral_source_category",
        "referral_at",
        "referrer_id",
        "referrer_name",
        "referrer_phone_number",
        "referrer_homeclub",
        "referee_id",
        "referee_name",
        "referee_phone",
        "referral_status",
        "num_reward_days",
        "transaction_id",
        "transaction_status",
        "transaction_at",
        "transaction_location",
        "transaction_type",
        "updated_at",
        "reward_granted_at",
        "is_business_logic_valid",
    ]

    final_dataset = referral_dataset[
        final_columns
    ].copy()

    # --------------------------------------------------------
    # Handle missing text values
    # --------------------------------------------------------

    text_columns = [
        "referral_source_category",
        "referrer_id",
        "referrer_name",
        "referrer_phone_number",
        "referrer_homeclub",
        "referee_id",
        "referee_name",
        "transaction_id",
        "transaction_status",
        "transaction_location",
        "transaction_type",
    ]

    for column in text_columns:

        final_dataset[column] = (
            final_dataset[column]
            .fillna("Unknown")
            .astype(str)
        )

    # --------------------------------------------------------
    # Handle reward-granted timestamp limitation
    # --------------------------------------------------------
    #
    # We cannot derive this timestamp from the supplied source
    # relationships. "Not Available" clearly communicates that
    # the value could not be established from source data.
    # --------------------------------------------------------

    final_dataset[
        "reward_granted_at"
    ] = final_dataset[
        "reward_granted_at"
    ].fillna("Not Available")

    # --------------------------------------------------------
    # Handle missing datetime values
    # --------------------------------------------------------
    #
    # A missing transaction timestamp means that there was no
    # transaction timestamp supplied for that referral.
    # We represent this explicitly rather than creating a fake
    # date.
    # --------------------------------------------------------

    datetime_columns = [
        "referral_at",
        "transaction_at",
        "updated_at",
    ]

    for column in datetime_columns:

        final_dataset[column] = (
            final_dataset[column]
            .fillna("Not Available")
        )

    # --------------------------------------------------------
    # String adjustment
    # --------------------------------------------------------
    #
    # Initcap is applied to descriptive string fields.
    # Identifiers and phone numbers are intentionally preserved.
    # Club names are explicitly excluded as required by the test.
    # --------------------------------------------------------

    initcap_columns = [
        "referral_source",
        "referral_source_category",
        "referrer_name",
        "referee_name",
        "referral_status",
        "transaction_status",
        "transaction_location",
        "transaction_type",
    ]

    for column in initcap_columns:

        final_dataset[column] = (
            final_dataset[column]
            .astype(str)
            .str.title()
        )

    # --------------------------------------------------------
    # Ensure boolean type
    # --------------------------------------------------------

    final_dataset[
        "is_business_logic_valid"
    ] = final_dataset[
        "is_business_logic_valid"
    ].astype(bool)

    return final_dataset


# ============================================================
# VALIDATION
# ============================================================

def validate_final_output(final_dataset):
    """
    Validate the final report against the required structure.
    """

    expected_columns = [
        "referral_details_id",
        "referral_id",
        "referral_source",
        "referral_source_category",
        "referral_at",
        "referrer_id",
        "referrer_name",
        "referrer_phone_number",
        "referrer_homeclub",
        "referee_id",
        "referee_name",
        "referee_phone",
        "referral_status",
        "num_reward_days",
        "transaction_id",
        "transaction_status",
        "transaction_at",
        "transaction_location",
        "transaction_type",
        "updated_at",
        "reward_granted_at",
        "is_business_logic_valid",
    ]

    # Row count.
    if len(final_dataset) != 46:
        raise ValueError(
            f"Expected 46 rows, found {len(final_dataset)}."
        )

    # Column count.
    if len(final_dataset.columns) != 22:
        raise ValueError(
            f"Expected 22 columns, "
            f"found {len(final_dataset.columns)}."
        )

    # Column names and order.
    if list(final_dataset.columns) != expected_columns:
        raise ValueError(
            "Final columns do not match the required output."
        )

    # Duplicate referral IDs.
    duplicate_referrals = (
        final_dataset["referral_id"]
        .duplicated()
        .sum()
    )

    if duplicate_referrals != 0:
        raise ValueError(
            "Duplicate referral_id values found."
        )

    # No actual Pandas null values.
    if final_dataset.isna().any().any():

        null_columns = (
            final_dataset.isna()
            .sum()
        )

        null_columns = (
            null_columns[
                null_columns > 0
            ]
        )

        raise ValueError(
            "Null values remain in final output:\n"
            f"{null_columns}"
        )

    print(
        "\nFinal validation passed!"
    )

    print(
        f"Rows validated: {len(final_dataset)}"
    )

    print(
        f"Columns validated: {len(final_dataset.columns)}"
    )

    print(
        "Duplicate referral IDs: 0"
    )

    print(
        "Null values: 0"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    # 1. Load all source tables.
    data = load_data()

    # 2. Clean source data.
    data = clean_data(data)

    # 3. Build the joined referral dataset.
    referral_dataset = build_referral_dataset(
        data
    )

    # 4. Convert timestamps to local time.
    referral_dataset = convert_timestamps(
        referral_dataset
    )

    # 5. Apply business logic.
    referral_dataset = apply_business_logic(
        referral_dataset
    )

    # 6. Prepare final report.
    final_dataset = prepare_final_output(
        referral_dataset
    )

    # 7. Validate final report.
    validate_final_output(
        final_dataset
    )

    # 8. Create output directory.
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # 9. Save final CSV.
    output_path = (
        OUTPUT_DIR
        / "referral_dataset.csv"
    )

    final_dataset.to_csv(
        output_path,
        index=False,
    )

    print(
        "\nReferral dataset created successfully!"
    )

    print(
        f"Final report saved to: {output_path}"
    )


# ============================================================
# RUN PIPELINE
# ============================================================

if __name__ == "__main__":
    main()