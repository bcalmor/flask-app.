# Flask User Management Application

This project is a simple web application built using Flask that allows users to register, log in, and manage their accounts. User data is stored in a JSON file.

## Project Structure

```
flask-app
├── app
│   ├── __init__.py
│   ├── routes.py
│   ├── models.py
│   ├── static
│   │   └── styles.css
│   └── templates
│       ├── base.html
│       ├── home.html
│       ├── login.html
│       └── register.html
├── data
│   └── users.json
├── requirements.txt
├── config.py
└── README.md
```

## Features

- User registration
- User login
- Homepage with navigation
- Data stored in JSON format

## Setup Instructions

1. Clone the repository:
   ```
   git clone <repository-url>
   cd flask-app
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the application:
   ```
   python -m flask run
   ```

4. Open your web browser and go to `http://127.0.0.1:5000` to access the homepage.

## Usage

- Navigate to the registration page to create a new account.
- Use the login page to access your account.
- The homepage provides links to both login and registration.

## License

This project is licensed under the MIT License.