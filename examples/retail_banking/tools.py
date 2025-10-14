import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

#  Some parts of the code are from Rasa.
#  Repo: https://github.com/rasa-customers/starterpack-retail-banking-en

class Database:
    table_definitions = {
        "users": {
            "create_statement": """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    phone TEXT,
                    address TEXT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    segment TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """,
            "insert_statement": "INSERT INTO users (name, email, phone, address, username, password, segment) VALUES (?, ?, ?, ?, ?, ?, ?)",
        },
        "accounts": {
            "create_statement": """
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER,
                    balance REAL,
                    type TEXT,
                    number TEXT,
                    sort_code TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            """,
            "insert_statement": "INSERT INTO accounts (user_id, balance, type, number, sort_code) VALUES (?, ?, ?, ?, ?)",
        },
        "transactions": {
            "create_statement": """
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY,
                    account_id INTEGER,
                    amount REAL,
                    datetime DATETIME,
                    description TEXT,
                    payment_method TEXT,
                    payee TEXT,
                    FOREIGN KEY(account_id) REFERENCES accounts(id)
                )
            """,
            "insert_statement": """
                INSERT INTO transactions (account_id, amount, datetime, description, payment_method, payee)
                VALUES (
                    ?,
                    ?,
                    datetime('now', '-' || (ABS(random()) % 90) || ' days',
                                    '-' || (ABS(random()) % 24) || ' hours',
                                    '-' || (ABS(random()) % 60) || ' minutes',
                                    '-' || (ABS(random()) % 60) || ' seconds'),
                    ?,
                    ?,
                    ?
                )
            """,
        },
        "payees": {
            "create_statement": """
                CREATE TABLE IF NOT EXISTS payees (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER,
                    name TEXT,
                    sort_code TEXT,
                    account_number TEXT,
                    type TEXT,
                    reference TEXT,
                    added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            """,
            "insert_statement": "INSERT INTO payees (user_id, name, sort_code, account_number, type, reference) VALUES (?, ?, ?, ?, ?, ?)",
        },
        "cards": {
            "create_statement": """
                CREATE TABLE IF NOT EXISTS cards (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER,
                    account_id INTEGER,
                    number TEXT UNIQUE,
                    type TEXT,
                    status TEXT,
                    issued_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id),
                    FOREIGN KEY(account_id) REFERENCES accounts(id)
                )
            """,
            "insert_statement": "INSERT INTO cards (user_id, account_id, number, type, status) VALUES (?, ?, ?, ?, ?)",
        },
        "branches": {
            "create_statement": """
                CREATE TABLE IF NOT EXISTS branches (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    address TEXT NOT NULL,
                    distance_km REAL
                )
            """,
            "insert_statement": "INSERT INTO branches (name, address, distance_km) VALUES (?, ?, ?)",
        },
        "advisors": {
            "create_statement": """
                CREATE TABLE IF NOT EXISTS advisors (
                    id INTEGER PRIMARY KEY,
                    branch_id INTEGER,
                    name TEXT,
                    email TEXT,
                    phone TEXT,
                    position TEXT,
                    FOREIGN KEY(branch_id) REFERENCES branches(id)
                )
            """,
            "insert_statement": "INSERT INTO advisors (branch_id, name, email, phone, position) VALUES (?, ?, ?, ?, ?)",
        },
        "appointments": {
            "create_statement": """
                CREATE TABLE IF NOT EXISTS appointments (
                    id INTEGER PRIMARY KEY,
                    advisor_id INTEGER,
                    date DATE,
                    start_time TIME,
                    end_time TIME,
                    status TEXT,
                    FOREIGN KEY(advisor_id) REFERENCES advisors(id)
                )
            """,
            "insert_statement": "INSERT INTO appointments (advisor_id, date, start_time, end_time, status) VALUES (?, ?, ?, ?, ?)",
        },
    }

    def __init__(self, database_path: Optional[Path] = None) -> None:
        """Initialise the database, creating or loading the schema and data as necessary."""
        self.project_root_path = Path(__file__).resolve().parent / "examples" / "retail_banking"
        self.database_path = (
            database_path or self.project_root_path / "banking.db"
        )
        self.source_data_path = self.project_root_path / "source"

        self.logger = self.setup_logger()

        try:
            if self.database_path.exists():
                self.logger.info(f"Loading existing database '{self.database_path}'")
                self.connection = sqlite3.connect(str(self.database_path))
            else:
                self.logger.info(f"Creating new in-memory database")
                self.connection = sqlite3.connect(":memory:")
                self.create_schema()
                self.load_data()
                self.save_to_disk()

            self.cursor = self.connection.cursor()

        except sqlite3.Error as e:
            self.logger.error(f"Error initialising database: {e}")
            raise

    def setup_logger(self) -> logging.Logger:
        """Set up logging configuration."""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            "%(asctime)s %(levelname)8s %(name)s  - %(message)s"
        )

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        return logger

    def create_schema(self) -> None:
        """Create the database schema."""
        try:
            for table, definition in self.table_definitions.items():
                self.logger.debug(f"Creating table '{table}'")
                self.connection.execute(definition["create_statement"])

            self.connection.commit()
            self.logger.info("Database schema created")
        except sqlite3.Error as e:
            self.logger.error(f"Error creating schema: {e}")
            raise

    def load_data(self) -> None:
        """Load data from JSON files into the database."""
        for source_file in self.source_data_path.glob("*.json"):
            with open(source_file, "r", encoding="utf-8") as file:
                data = json.load(file)
                table_name = source_file.stem.lower()
                self.logger.info(
                    f"Attempting to load data for table '{table_name}' from {source_file}"
                )
                if table_name in self.table_definitions:
                    self.insert_data(table_name, data)
                else:
                    self.logger.warning(f"Skipping unknown table '{table_name}'")

    def insert_data(self, table_name: str, data: List[Dict[str, Any]]) -> None:
        """Insert data into the specified table."""
        if table_name not in self.table_definitions:
            self.logger.error(f"Unknown table: {table_name}")
            raise ValueError(f"Unknown table: {table_name}")

        insert_statement = self.table_definitions[table_name]["insert_statement"]
        try:
            for row in data:
                self.connection.execute(insert_statement, tuple(row.values()))

            self.connection.commit()
            self.logger.info(f"Inserted {len(data)} records into table '{table_name}'")
        except sqlite3.Error as e:
            self.logger.error(f"Error inserting data into table '{table_name}': {e}")
            raise

    def save_to_disk(self) -> None:
        """Save the in-memory database to disk."""
        try:
            with sqlite3.connect(str(self.database_path)) as backup_db:
                self.connection.backup(backup_db)
            self.logger.info(f"Database saved to {self.database_path}")
        except sqlite3.Error as e:
            self.logger.error(f"Error saving database to disk: {e}")
            raise

    def run_query(
        self, query: str, parameters: Tuple = (), one_record: bool = True
    ) -> Union[Tuple, List[Tuple]]:
        """Run a query with the given parameters and return the result."""
        try:
            self.cursor.execute(query, parameters)

            if one_record:
                return self.cursor.fetchone()
            else:
                return self.cursor.fetchall()
        except sqlite3.Error as e:
            self.logger.error(f"Error running query: {e}")
            raise

    def __enter__(self):
        """Enter the runtime context related to this object."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Exit the runtime context related to this object."""
        self.connection.close()
        self.logger.info("Database connection closed")


def action_ask_account_from(username):
    db = Database()
    query = """
                SELECT a.id, a.type, a.balance, a.number
                FROM accounts a
                JOIN users u ON a.user_id = u.id
                LEFT JOIN cards c ON a.id = c.account_id AND c.type = 'debit'
                WHERE u.name = ?
            """
    results = db.run_query(query, (username,), one_record=False)

    contents = [
        {
            "info": f"{account[1].title()} (Balance: ${account[2]:.2f})",
            "account_from": str(account[3]),
        }
        for account in results
    ]
    print(f"account information: {contents}")
    return

def action_check_payee_existence(username, payee_name):
    db = Database()
    user_query = "SELECT id FROM users WHERE name = ?"
    user_result = db.run_query(user_query, (username,), one_record=True)
    if user_result is None:
        print("The user does not exist.")
        return
    user_id = user_result[0]

    check_payee_query = "SELECT id FROM payees WHERE user_id = ? AND name = ?"
    payee_result = db.run_query(
        check_payee_query, (user_id, payee_name), one_record=True
    )

    if payee_result:
        print("The payee exists.")
        return
    print("The payee does not exist.")
    return [{"bot": f"{payee_name} is not an authorised payee. Let's add them!"}]


def action_check_sufficient_funds(account_from, amount: float):
    db = Database()
    query = "SELECT balance FROM accounts WHERE number = ?"
    result = db.run_query(query, (account_from,), one_record=True)

    if result:
        current_balance = float(result[0])
        if current_balance >= amount:
            print("sufficient funds.")
            return

    print("insufficient funds.")
    return


def action_validate_payment_date(payment_date):
    def is_future_date(payment_date_str: str) -> bool:
        current_date = datetime.today().date()
        payment_date = datetime.strptime(payment_date_str, "%d/%m/%Y").date()
        return payment_date > current_date

    if is_future_date(payment_date):
        print("It is a future payment date.")
        return
    else:
        print("It is not a future payment date.")
        return


def action_process_immediate_payment():
    print("payment processed.")
    return


def action_schedule_payment():
    print("payment scheduled.")
    return


def action_remove_payee(username, payee_name):
    db = Database()

    user_query = "SELECT id FROM users WHERE name = ?"
    user_result = db.run_query(user_query, (username,), one_record=True)
    user_id = user_result[0]

    check_payee_query = "SELECT id FROM payees WHERE user_id = ? AND name = ?"
    payee_result = db.run_query(
        check_payee_query, (user_id, payee_name), one_record=True
    )

    if not payee_result:
        print(f"I'm sorry, but I couldn't find a payee named '{payee_name}'")
        return

    remove_query = "DELETE FROM payees WHERE user_id = ? AND name = ?"
    db.run_query(remove_query, (user_id, payee_name), one_record=False)
    db.connection.commit()

    print("Remove payee success.")
    return


def action_list_payees(username):
    db = Database()
    query = """
            SELECT p.id, p.name, p.account_number
            FROM payees p
            JOIN users u ON p.user_id = u.id
            WHERE u.name = ?
            """
    results = db.run_query(query, (username,), one_record=False)

    payee_names = [payee[1] for payee in results]
    if len(payee_names) > 1:
        payees_list = ", ".join(payee_names[:-1]) + " and " + payee_names[-1]
    else:
        payees_list = payee_names[0] if payee_names else ""

    message = f"You are authorised to transfer money to: {payees_list}"
    print(message)

    return


def action_check_balance(username, account):
    db = Database()

    user_query = "SELECT id FROM users WHERE name = ?"
    user_result = db.run_query(user_query, (username,), one_record=True)
    user_id = user_result[0]

    check_balance_query = (
        "SELECT balance FROM accounts WHERE user_id = ? AND number = ?"
    )
    balance_result = db.run_query(
        check_balance_query, (user_id, account), one_record=True
    )

    current_balance = float(balance_result[0])

    message = f"The balance is: ${current_balance}"
    print(message)
    return


def action_ask_account(username):
    db = Database()
    query = """
                SELECT a.user_id, a.number, a.type
                FROM accounts a
                JOIN users u ON a.user_id = u.id
                WHERE u.name = ?
            """
    results = db.run_query(query, (username,), one_record=False)

    content = [
        {
            "account_information": f"{account[1]} ({account[2].title()})",
            "account_number": str(account[1]),
        }
        for account in results
    ]

    print(f"Here's the account information: {content}")
    return


def action_session_start(username):
    db = Database()
    query = """
                SELECT name, segment, email, address
                FROM users
                WHERE name = ?
            """
    result = db.run_query(query, (username,), one_record=True)

    if result:
        username, segment, email, address = result
        return [
            {"arg": "segment", "value": segment},
            {"arg": "email_address", "value": email},
            {"arg": "physical_address", "value": address},
        ]
    else:
        return


def action_update_card_status(username, card):
    new_status = "inactive"

    db = Database()
    update_query = """
                UPDATE cards
                SET status = ?
                WHERE number = ? AND user_id = (
                    SELECT id FROM users WHERE name = ?
                )
            """
    db.cursor.execute(update_query, (new_status, card, username))
    db.connection.commit()
    print("success")
    return


def action_ask_card(username):
    db = Database()
    query = """
                SELECT c.user_id, c.number, c.type
                FROM cards c
                JOIN users u ON c.user_id = u.id
                WHERE u.name = ?
            """
    results = db.run_query(query, (username,), one_record=False)

    content = [
        {
            "card_information": f"{i + 1}: x{account[1][-4:]} ({account[2].title()})",
            "card": f"{str(account[1])}",
        }
        for i, account in enumerate(results)
    ]
    message = "Select the card you require assistance with:"
    print(f"{message}: {content}")

    return


def action_add_payee(username, payee_name, account_number, payee_type, reference):
    sort_code = "111111"
    db = Database()
    user_query = "SELECT id FROM users WHERE name = ?"
    user_result = db.run_query(user_query, (username,), one_record=True)
    user_id = user_result[0]

    insert_query = """
            INSERT INTO payees (user_id, name, sort_code, account_number, type, reference)
            VALUES (?, ?, ?, ?, ?, ?)
            """
    db.run_query(
        insert_query,
        (
            user_id,
            payee_name,
            sort_code,
            account_number,
            payee_type,
            reference,
        ),
        one_record=False,
    )
    db.connection.commit()
    return