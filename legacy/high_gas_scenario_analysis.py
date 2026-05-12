import pandas as pd

data = pd.read_excel(r"C:\Users\eduar\OneDrive\Desktop\PythonProjects\Ammonia Project\pythonProject1\NOVEMBER AP Model\v14_DATASET_monthly_highgas.xlsx")

# do a groupby ["time", "scenario"] and save the describe to excel file with multiple sheets'
file_name = r"C:\Users\eduar\OneDrive\Desktop\PythonProjects\Ammonia Project\pythonProject1\NOVEMBER AP Model\v14_DATASET_monthly_highgas_description.xlsx"
data.groupby(["time", "scenario"]).describe().to_excel(file_name)
