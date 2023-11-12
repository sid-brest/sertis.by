import os

# Define the folder path and the rows to replace
folder_path = "./"
rows_to_replace = [ 
    ("team.html\">Сотрудники","javascript:void(0)\">Сотрудники"),
    ("testimonials.html\">Отзывы","javascript:void(0)\">Отзывы"),
    ("services.html\">Подтверждение cоответствия","javascript:void(0)\">Подтверждение cоответствия"),
    ("services.html\">Оценка системы производственного контроля","javascript:void(0)\">Оценка системы производственного контроля"),
    ("services.html\">Оценка пригодности","javascript:void(0)\">Оценка пригодности"),
    ("services.html\">Дополнительные услуги","javascript:void(0)\">Дополнительные услуги"),
    ("<li><a href=\"pricing.html\">Цены</a></li>","<!-- <li><a href=\"pricing.html\">Цены</a></li> -->")
]

# Iterate over all files in the folder
for filename in os.listdir(folder_path):
    if filename.endswith(".html"):
        file_path = os.path.join(folder_path, filename)
        
        # Read the contents of the file
        with open(file_path, "r", encoding="utf-8") as file:
            file_content = file.read()
        
        # Replace the rows in the file content
        for old_row, new_row in rows_to_replace:
            file_content = file_content.replace(old_row, new_row)
        
        # Write the modified content back to the file
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(file_content)