import pandas as pd
import re
import time
import requests
import sys
import gspread
from google.oauth2.service_account import Credentials

sys.stdout.reconfigure(encoding='utf-8')

# Google Sheets settings
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

SERVICE_ACCOUNT_FILE = 'credentials.json'
SPREADSHEET_NAME = 'InstagramProfiles'  # Your Google Sheet name
SHEET_NAME = 'Sheet1'  # Tab name

# Instagram headers and cookies
HEADERS = {
    "User-Agent": "Instagram 219.0.0.12.117 Android",
    "X-IG-App-ID": "936619743392459"
}
COOKIES = {
    "sessionid": "69469919129%3A8h8s58Dhli3fhV%3A23%3AAYdn7OuoeWBZJh1tBUpJlpUH-tLrSrSVb-gSLlXWNw",
    "ds_user_id": "69469919129",
    "csrftoken": "6EnJqMu0G-4gEXiKcbiifm"
}

def extract_username(link):
    if isinstance(link, str):
        match = re.search(r"instagram\.com/([^/?#]+)/?", link)
        if match:
            return match.group(1)
    return None

def fetch_profile(username):
    url = f"https://i.instagram.com/api/v1/users/web_profile_info/?username={username}"
    try:
        response = requests.get(url, headers=HEADERS, cookies=COOKIES)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            print(f"[!] 401 Unauthorized for {username} — sleeping 10s...")
            time.sleep(10)
        else:
            print(f"[!] Error {response.status_code} for {username}")
    except Exception as e:
        print(f"[!] Exception for {username}: {str(e)}")
    return None

def main():
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open(SPREADSHEET_NAME).worksheet(SHEET_NAME)

    data = sheet.get_all_records()
    df = pd.DataFrame(data)

    # Clean column names for safety
    df.columns = [col.strip() for col in df.columns]

    if "Instagram Link" not in df.columns or "Followers" not in df.columns or "Creators Bio" not in df.columns:
        print("[X] Required columns ('Instagram Link', 'Followers', 'Creators Bio') are missing.")
        return

    skipped_profiles = []

    for index, row in df.iterrows():
        username = extract_username(row["Instagram Link"])
        if not username:
            print(f"SKIPPED:Invalid link at row {index + 2}", flush=True)
            skipped_profiles.append(f"Row {index + 2}: Invalid link")
            continue

        print(f"[~] Fetching data for {username}...", flush=True)
        profile_data = fetch_profile(username)

        if profile_data and "data" in profile_data:
            user_info = profile_data["data"].get("user", {})
            followers = user_info.get("edge_followed_by", {}).get("count", 0)
            bio = user_info.get("biography", "")

            df.at[index, "Followers"] = followers
            df.at[index, "Creators Bio"] = bio
            print(f"[✓] Updated: {username} - {followers} followers", flush=True)
        else:
            print(f"SKIPPED:{username}", flush=True)
            skipped_profiles.append(username)

        percent = int(((index + 1) / len(df)) * 100)
        print(f"PROGRESS:{percent}", flush=True)
        time.sleep(2)

    # Final verification print
    print("\n[🔍] Sample of final DataFrame:")
    print(df[["Instagram Link", "Followers", "Creators Bio"]].head())

    # Update the sheet with final cleaned values
    followers_col_index = df.columns.get_loc("Followers")
    bio_col_index = df.columns.get_loc("Creators Bio")

    followers_data = [[str(df.at[i, "Followers"])] for i in range(len(df))]
    bio_data = [[df.at[i, "Creators Bio"]] for i in range(len(df))]

    sheet.update(values=followers_data, range_name=f"{chr(65 + followers_col_index)}2:{chr(65 + followers_col_index)}{len(df)+1}")
    sheet.update(values=bio_data, range_name=f"{chr(65 + bio_col_index)}2:{chr(65 + bio_col_index)}{len(df)+1}")

    if skipped_profiles:
        print("SKIPPED_SUMMARY_START", flush=True)
        for user in skipped_profiles:
            print(user, flush=True)
        print("SKIPPED_SUMMARY_END", flush=True)

    print(f"[✔] Google Sheet '{SPREADSHEET_NAME}' updated successfully with followers and bio.")

if __name__ == "__main__":
    main()
