# auth.py
import os

def is_unique_username(username):
    # Check if the username already exists in account.txt
    with open('account.txt', 'r', encoding='utf-8') as file:
        lines = file.readlines()
        return username not in [line.split(',')[0] for line in lines]

def save_user_info(username, password):
    # Save the user information to account.txt
    with open('account.txt', 'a', encoding='utf-8') as file:
        file.write(f'{username},{password}\n')

def authenticate_user(username, password):
    # Authenticate the user against account.txt
    with open('account.txt', 'r', encoding='utf-8') as file:
        lines = file.readlines()
        return f'{username},{password}\n' in lines
