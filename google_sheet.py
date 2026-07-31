import gspread
from google.oauth2.service_account import Credentials
from google.auth.exceptions import TransportError
import os
import csv

class Answer():
    def __init__(self, name, represent, mission, description, discord, username) -> None:
        self.name = name
        self.represent = represent
        self.mission = mission
        self.description = description
        self.discord = discord
        self.username = username

    def __eq__(self, other) -> bool:
        if self.name == other.name and self.mission == other.mission and self.description == other.description:
            return True
        else:
            return False

    def __repr__(self) -> str:
        return f"{self.name}, {self.represent}, {self.mission}, {self.description}, {self.discord}, {self.username}"

    def __str__(self) -> str:
        return f"{self.name}, {self.represent}, {self.mission}, {self.description}, {self.discord}, {self.username}"

def get_creds():
    cred = ""
    files: list = os.listdir()
    creds: list[list[str, int, int]] = []

    for file in files:
        file: list = file.split("-")
        if len(file) == 3:
            file_sp = file[-1].split(".")
            if not file_sp[-1] == "json":
                continue
            creds.append(file)
            print("Heidrun || Cred file found")

    if len(creds) == 1:
        cred = creds[0]
    elif not creds:
        print("Heidrun || Error: No Cred file could be found")
        cred = None
        return
    else:
        for index, file in enumerate(creds):
            print(f"[{index+1}] {file}")
        
        while True:
            select = int(input("Select cred with ID: "))
            if 0 <= select-1 <= len(creds):
                cred = creds[select-1]
                break
    
    cred2 = ""
    for index, cre in enumerate(cred):
        if index+1 == len(cred):
            cred2 += cre
        else:
            cred2 += f"{cre}-"

    dir = os.getcwd()
    cred = os.path.join(dir, cred2)
    print(f"Heidrun || Selected cred file: {cred2}")
    return cred

def google_read(_creds) -> list:
    scope = ["https://www.googleapis.com/auth/spreadsheets.readonly", "https://www.googleapis.com/auth/drive"]
    cred = _creds
    if cred is None:
        print("Heidrun || Error: Kan inte läsa från google spreadsheet...")
        return []
    creds = Credentials.from_service_account_file(cred, scopes=scope)
    gc = gspread.authorize(creds)
    sheet = gc.open("Grafikförfråga - BM").sheet1
    print("Heidrun || Spreadsheet hittad!")
    answers = []
    for row in sheet.get_all_values()[1:]:
        answer = Answer(*row[1:])

        if answer.discord == "Ja / Yes":
            answer.discord = True
        else:
            answer.discord = False

        answers.append(answer)
    return answers

def old_read(filename = "previous_projects.csv") -> list:
    answers = []
    try:
        with open(filename, "r", encoding="utf-8") as save:
            rows = csv.reader(save, skipinitialspace=True)
            lines = list(rows)
            for row in lines[1:]:
                if not row:
                    continue
                answer = Answer(*row[:6])
                answers.append(answer)
        return answers
    except FileNotFoundError:
        print(f"Heidrun || Error: {filename} kunde inte hittas...")