import requests

def register_user(username, password, role_id):
    try:
        url = "http://localhost:5000/auth/register"
        payload = {
            "username": username,
            "password": password,
            "role_id": role_id  # 1 - Admin, 2 - worker, 3 - User
        }

        response = requests.post(url, json=payload)

        if response.status_code == 201:
            print(f"User '{username}' registered successfully.")
        else:
            print(f"Registration error: {response.json().get('message', 'Unknown error')}")
    except requests.exceptions.ConnectionError:
        print("Could not connect to server. Check if server is running.")
    except Exception as e:
        print(f"Error occurred: {e}")


if __name__ == "__main__":
    username = "user"
    password = "user"
    role_id = 3

    register_user(username, password, role_id)
