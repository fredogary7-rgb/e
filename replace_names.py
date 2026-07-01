import os

def replace_in_html_files(root_dir, replacements):
    count = 0
    # Parcourir tous les dossiers et fichiers à partir de la racine
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            # On cible uniquement les fichiers .html
            if filename.endswith('.html'):
                file_path = os.path.join(dirpath, filename)
                
                # Lire le contenu du fichier
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                    content = file.read()
                
                # Vérifier si l'un des mots existe dans le fichier
                file_modified = False
                new_content = content
                
                for old_word, new_word in replacements.items():
                    if old_word in new_content:
                        new_content = new_content.replace(old_word, new_word)
                        file_modified = True
                
                # Réécrire le fichier uniquement s'il y a eu un changement
                if file_modified:
                    with open(file_path, 'w', encoding='utf-8') as file:
                        file.write(new_content)
                    print(f"[MODIFIÉ] {file_path}")
                    count += 1
                    
    print(f"\n✨ Remplacement terminé ! {count} fichier(s) HTML modifié(s).")

if __name__ == "__main__":
    # Définir le dossier où se trouvent tes templates
    target_directory = "./templates" 
    
    # Dictionnaire des correspondances (Ancien nom -> Nouveau nom)
    mapping = {
        "NovaTrade": "NectarPro",
        "Novatrade": "NectarPro",
        "novatrade": "nectarpro"
    }
    
    # Lancement du script
    replace_in_html_files(target_directory, mapping)

