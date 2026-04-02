import google.auth

def inspect():
    try:
        credentials, project = google.auth.default()
        print(f"Project: {project}")
        print(f"Creds type: {type(credentials)}")
        
        if hasattr(credentials, 'account'):
            print(f"account value: '{credentials.account}'")
        if hasattr(credentials, '_account'):
            print(f"_account value: '{credentials._account}'")
        if hasattr(credentials, 'service_account_email'):
            print(f"SA Email: {credentials.service_account_email}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect()
