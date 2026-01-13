import os
import subprocess
import argparse

def generate_groups(folder, separator):
    groups = {}
    for filename in os.listdir(folder):
        if filename.endswith('.pdf'):
            group_name = filename.split(separator if separator is not None else '-Premier-')[0]
            
            if group_name not in groups:
                groups[group_name] = [filename]
            else:
                groups[group_name].append(filename)
    return groups
def f(n):
    return f"\"{n}\""
def generate_batch(folder, folderMerge, separator):
    groups = generate_groups(folder, separator)
    cmdd = r"\generate-byannexe.bat"
    with open(folder + cmdd, "w") as file:
        for group, files in groups.items():
            ouname = f"{folderMerge}\\({str(len(files)).zfill(3)}){group}.pdf"
            mappa = list(map(f,files))
            command = f"pdftk {' '.join(mappa)} cat output \"{ouname}\"\n"
            # print(f"processing {len(files)} cat output {group}.pdf")
            file.writelines(command)

def create_folder_if(folder, folderMerge):
    subfolder = folderMerge.replace('/','').replace('\\','')
    condition = not os.path.isabs(folderMerge) or folderMerge.startswith('/')
    folder_name = folder + "\\" + subfolder if condition else folderMerge
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

def exec_batch(folder):
    try:
        cmdTry = f'cd "{folder}" && generate-byannexe'
        subprocess.run(cmdTry, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")

def main(args):
    create_folder_if(args.folder, args.folder_merge)
    generate_groups(args.folder, args.separator)
    generate_batch(args.folder, args.folder_merge, args.separator)
    exec_batch(args.folder)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Group by name separator to merge")
    parser.add_argument("--folder", type=str, help="Folder where the pdfs groups are located")
    parser.add_argument("--separator", type=str, help="The separator to extract the group names")
    parser.add_argument("--folder-merge", type=str, help="Folder where to put the merged Groups files")

    args = parser.parse_args()
    main(args)

# cls && python groupin-names.py --folder "C:\Users\USER\Documents\Notices de vendredi 22 décembre 2023"  --folder-merge C:\Users\USER\Documents\ExcelToPDFs\merged