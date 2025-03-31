import pandas as pd
import re


def convert_text_to_excel(input_file_path, output_excel_path):
    """
    Convert text file with student data to Excel format

    Format of each line in text file:
    NAME - email@example.com - Password
    """
    # Lists to store parsed data
    names = []
    emails = []
    passwords = []

    # Read the input file
    with open(input_file_path, 'r') as file:
        for line in file:
            # Skip empty lines
            if not line.strip():
                continue

            # Split by ' - ' to get the three components
            parts = line.strip().split(' - ')

            # Only process lines that have the expected format
            if len(parts) == 3:
                name = parts[0]
                email = parts[1]
                password = parts[2]

                names.append(name)
                emails.append(email)
                passwords.append(password)
            else:
                print(f"Skipping malformatted line: {line.strip()}")

    # Create DataFrame
    df = pd.DataFrame({
        'Name': names,
        'Email': emails,
        'Password': passwords
    })

    # Save to Excel
    df.to_excel(output_excel_path, index=False)
    print(f"Successfully converted data to Excel file: {output_excel_path}")
    print(f"Total records processed: {len(names)}")


# Example usage
if __name__ == "__main__":
    input_file = "todo.txt"  # Change this to your input file path
    output_file = "student_data.xlsx"  # Change this to your desired output file path

    convert_text_to_excel(input_file, output_file)