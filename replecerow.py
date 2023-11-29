import os

# Define the folder path and the rows to replace
folder_path = "./"
rows_to_replace = [ 
    ("<a href=\"https://t.me/sertis_by\" class=\"telegram\"><i class=\"bx bxl-telegram\"></i></a>","<a href=\"https://t.me/sertis_by\" target=\"_blank\" class=\"telegram\"><i class=\"bx bxl-telegram\"></i></a>"),
    ("<a href=\"https://www.facebook.com/pposertis\" class=\"facebook\"><i class=\"bx bxl-facebook\"></i></a>","<a href=\"https://www.facebook.com/pposertis\" target=\"_blank\" class=\"facebook\"><i class=\"bx bxl-facebook\"></i></a>"),
    ("<a href=\"https://www.linkedin.com/company/sertisbrest\" class=\"linkedin\"><i class=\"bx bxl-linkedin\"></i></a>","<a href=\"https://www.linkedin.com/company/sertisbrest\" target=\"_blank\" class=\"linkedin\"><i class=\"bx bxl-linkedin\"></i></a>"),

    
]
# Iterate over all files in the folder
for filename in os.listdir(folder_path):
    if filename.endswith("html"):
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