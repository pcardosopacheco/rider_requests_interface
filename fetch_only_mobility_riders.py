import os
import requests
import csv
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load env variables
load_dotenv()

# Logging
log_filename = "fetch_data_log.log"
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler(log_filename), logging.StreamHandler()])

def fetch_data(url, data_type, cutoff_timestamp=None, created_interface=None):
    """
    Fetch data from the Spare API and return as a list of dict.
    """
    token = os.getenv('SPARELABS_API_TOKEN')
    if not token:
        raise ValueError("API token is missing, set the token in the .env file.")

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    all_data = []

    # Fetch data page by page until all data is retrieved or until data older than cutoff_timestamp is reached
    page = 1
    while True:
        params = {'limit': 50, 'skip': (page - 1) * 50}
        if cutoff_timestamp:
            params['fromCreatedAt'] = cutoff_timestamp
        if created_interface:
            params['createdInterface'] = created_interface

        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            logging.error(f"Failed to fetch {data_type} data: {response.status_code} - {response.text}")
            response.raise_for_status()
        
        data = response.json()
        if not data or 'data' not in data:
            break
        
        all_data.extend(data['data'])

        # Log progress
        logging.info(f"Fetched {len(all_data)} {data_type} so far...")

        # If there are less than 50 records in the response, it means all data is fetched
        if len(data['data']) < 50:
            break

        page += 1

    logging.info(f"Fetched {len(all_data)} {data_type}.")
    return {'data': all_data}

def save_to_csv(data, filename, columns, process_row, folder):
    """
    Save the data to a CSV file.
    """
    if not os.path.exists(folder):
        os.makedirs(folder)

    file_path = os.path.join(folder, filename)

    with open(file_path, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(columns)
        
        for item in data["data"]:
            row = process_row(item)
            if row:
                writer.writerow(row)
    logging.info(f"Data successfully saved to {file_path}")

def process_rider_row(rider):
    """
    Process a single rider row for CSV.
    """
    default_accessibility_features = rider.get("defaultAccessibilityFeatures", [])
    if not default_accessibility_features:
        return None  # Skip riders without default accessibility features

    accessibility_features_types = ", ".join([feature.get("type", "") for feature in default_accessibility_features])
    
    row = [
        rider.get("id", ""),
        rider.get("externalNumericId", ""),
        rider.get("phoneNumber", ""),
        accessibility_features_types,
        rider.get("defaultNotes", ""),

    ]
    return row

def main():
    try:
        logging.info("Starting to fetch data...")
        current_date = datetime.now().strftime("%Y-%m-%d")
        folder = f"new_data{current_date}"

        # Fetch Riders
        riders_url = "https://api.sparelabs.com/v1/riders"
        riders_data = fetch_data(riders_url, 'riders')

        # Save to CSV only riders with default accessibility features
        riders_with_features_filename = f"riders_with_features_{current_date}.csv"
        rider_columns = [
            "ID",
            "External Numeric ID", 
            "Phone Number", 
            "Default Accessibility Features",
            "Default Notes"
        ]
        save_to_csv(riders_data, riders_with_features_filename, rider_columns, process_rider_row, folder)

        logging.info("Data processing and upload completed successfully.")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching data: {e}")
    except Exception as e:
        logging.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
