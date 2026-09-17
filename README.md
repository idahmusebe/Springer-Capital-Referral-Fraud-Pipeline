# Springer Capital Referral Fraud Detection Pipeline

## Project Overview

This project was developed as part of the Springer Capital Data Engineer Intern take-home test.

The objective is to build a data profiling and data processing pipeline for a referral program. The pipeline combines referral, user, reward, transaction, status, and lead data to produce a final referral report and apply business rules that identify potentially invalid referral rewards.

The solution is implemented in Python using Pandas and is containerized using Docker.

## Business Context

The referral program allows existing users (referrers) to bring new users (referees) to the platform.

The process records:

- Referral creation
- Referrer and referee information
- Referral status
- Referral rewards
- Related transactions
- Reward-granted events
- Lead information

The final pipeline brings these sources together and evaluates each referral against the defined business rules.

## Source Data

The pipeline processes the following seven CSV tables:

1. lead_log.csv
2. user_referrals.csv
3. user_referral_logs.csv
4. user_logs.csv
5. user_referral_statuses.csv
6. referral_rewards.csv
7. paid_transactions.csv

## Project Structure

Springer-Capital-Referral-Fraud-Pipeline/
│
├── data/
├── docs/
│   └── data_dictionary.xlsx
│
├── docker/
│   └── Dockerfile
│
├── output/
│   └── referral_dataset.csv
│
├── profiling/
│   └── profiling_results.csv
│
├── src/
│   ├── profile_data.py
│   └── referral_pipeline.py
│
├── tests/
│
├── requirements.txt
└── README.md
## Data Profiling

The profiling script examines all seven source tables.

The profiling includes:

- Row counts
- Column information
- Null counts
- Distinct value counts
- Data types

The profiling output is saved to:

profiling/profiling_results.csv

To run the profiling script:

python src/profile_data.py

## Data Processing Pipeline

The main pipeline performs the following steps.

### 1. Data Loading

All seven CSV files are loaded into Pandas DataFrames.

### 2. Data Cleaning

The pipeline:

- Removes unnecessary whitespace from string values
- Converts timestamp fields to datetime values
- Converts reward values to numeric values
- Handles missing values in the final output
- Standardizes descriptive string values

### 3. Joining Data Sources

The referral data is combined with:

- Referral statuses
- Referral rewards
- Paid transactions
- User information
- Lead information

The joins are performed using the relevant identifiers.

Duplicate referral records are checked after joining.

### 4. Timezone Conversion

Source timestamps are provided in UTC.

The pipeline converts timestamps to local time using the timezone information available in the relevant source tables.

For referral timestamps where a timezone is not directly available in user_referrals, the related referrer's home-club timezone is used.

### 5. Referral Source Category

The referral source category follows the business rules provided in the test:

- User Sign Up → Online
- Draft Transaction → Offline
- Lead → Lead's source_category
## Business Logic

The pipeline creates a boolean field called:

is_business_logic_valid

This field indicates whether each referral satisfies the business rules defined in the take-home test.

### Valid Condition 1

A referral reward is considered valid when all of the following conditions are satisfied:

1. The reward value is greater than 0.
2. The referral status is Berhasil.
3. The referral has a transaction ID.
4. The transaction status is PAID.
5. The transaction type is NEW.
6. The transaction occurred after the referral was created.
7. The transaction occurred in the same month as the referral creation.
8. The referrer's membership has not expired.
9. The referrer's account is not deleted.
10. The reward has been granted to the referee.

### Valid Condition 2

A referral is considered valid when:

1. The referral status is either Menunggu or Tidak Berhasil.
2. There is no reward value assigned.

### Invalid Referral Conditions

The pipeline also identifies referrals that do not satisfy the valid business conditions.

Examples include:

- A positive reward with a referral status other than Berhasil.
- A positive reward without a transaction ID.
- No reward value assigned despite having a qualifying transaction.
- A Berhasil referral with a missing or zero reward value.
- A transaction occurring before the referral was created.

The final boolean result is stored in is_business_logic_valid.
## Output

The final report is generated as:

output/referral_dataset.csv

The required output contains:

- 46 referral records
- 22 columns
- No duplicate referral IDs
- No null values

The final output includes referral details, referrer and referee information, referral status, reward information, transaction information, and the business-logic validation result.

## Data Dictionary

The output columns are documented in:

docs/data_dictionary.xlsx

The data dictionary explains:

- Column name
- Data type
- Business meaning
- Constraints and relevant notes

The document is designed to be understandable to both technical and business users.

## Requirements

The project uses:

- Python
- Pandas
- PySpark

The required Python dependencies are listed in:

requirements.txt
## Running the Project Locally

### 1. Create a Virtual Environment

On Windows PowerShell:

python -m venv .venv

Activate the virtual environment:

.\.venv\Scripts\Activate.ps1

### 2. Install Dependencies

Install the required Python packages:

pip install -r requirements.txt

### 3. Run Data Profiling

Run the profiling script:

python src/profile_data.py

The profiling results will be saved to:

profiling/profiling_results.csv

### 4. Run the Referral Pipeline

Run the main pipeline:

python src/referral_pipeline.py

The final report will be created at:

output/referral_dataset.csv
## Docker

Docker is used to containerize the pipeline and provide a reproducible execution environment.

### Build the Docker Image

From the project root, run:

docker build -f docker/Dockerfile -t springer-referral-pipeline .

### Run the Docker Container

Run the container with the output and profiling folders mounted to the local project:

docker run --rm -v "${PWD}/output:/app/output" -v "${PWD}/profiling:/app/profiling" springer-referral-pipeline

The output directory is mounted from the local project into the container so that the generated report is stored outside the container.

The final report will be available at:

output/referral_dataset.csv

## Validation

The pipeline performs final validation to confirm that:

- The output contains 46 rows
- The output contains 22 required columns
- Referral IDs are not duplicated
- Null values are not present in the final report

Example validation result:

Rows validated: 46
Columns validated: 22
Duplicate referral IDs: 0
Null values: 0

## Data Quality Note

The supplied user_referral_logs data contains reward-granted records whose identifiers could not be reliably matched to the referral records or transaction records.

Because of this source-data limitation, reward_granted_at cannot be reliably derived for those records without inventing a relationship that is not supported by the supplied data.

The pipeline therefore documents unavailable reward-granted timestamps explicitly rather than fabricating values.

## Project Deliverables

The repository contains:

- Python data profiling script
- Python referral processing pipeline
- Profiling results
- Final referral CSV report
- Dockerfile
- Data dictionary
- README documentation

## Author

Idah M. Musebe

Data Engineering / Data Analytics