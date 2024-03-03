import re, requests, base64, os
from bs4 import BeautifulSoup

config = {
    'target_site': 'https://bloxd.io/',
    'save_path': './extracted/',
}

site_parsed = BeautifulSoup(requests.get(config['target_site']).text, 'html.parser')
site_scripts = [sc['src'] for sc in site_parsed.find_all('script', src = True)]
main_script_url = config['target_site'].removesuffix('/') + site_scripts[-1]
main_script_content = requests.get(main_script_url).text

flags = re.IGNORECASE | re.MULTILINE
names_matches = re.finditer(r'\"\./(.+?)\":([0-9]+)', main_script_content, flags) # Catastrophic backtracking sitting here /!\
models_matches = re.finditer(r'([0-9]+):function\(.\){\"use strict\";.\.exports=\"(data:model/[^;]+;base64[^\"]+)', main_script_content, flags)
images_matches = re.finditer(r'([0-9]+):function\(.\){\"use strict\";.\.exports=\"(data:image/[^;]+;base64[^\"]+)', main_script_content, flags)
names, models, images = {}, {}, {}

for model_match in models_matches: models[model_match.group(1)] = model_match.group(2)
for image_match in images_matches: images[image_match.group(1)] = image_match.group(2)
for name_match in names_matches:
    if len(name_match.group(0)) < 128: names[name_match.group(2)] = name_match.group(1).replace(',', '')

models_save_path, images_save_path = f'{config["save_path"]}models/', f'{config["save_path"]}images/'
for path in [models_save_path, images_save_path]:
    if not os.path.exists(path): os.makedirs(path)

for index, data in (images | models).items():
    if index not in names: continue
    readable_texture_name = names[index]
    if readable_texture_name.endswith('.png'):
        print(f'Texture "{readable_texture_name}" (Index: {index}) extracted into {images_save_path}')
        with open(images_save_path + readable_texture_name, 'wb') as file:
            file.write(base64.b64decode(data.removeprefix('data:image/png;base64,').encode('ascii')))
    elif readable_texture_name.endswith('.glb'):
        with open(models_save_path + readable_texture_name, 'wb') as file:
            file.write(base64.b64decode(data.removeprefix('data:model/gltf-binary;base64,').encode('ascii')))
        print(f'Model "{readable_texture_name}" (Index: {index}) extracted into {models_save_path}')
    else:
        print(f'Unknown file format "{readable_texture_name}" (Index: {index}), cannot be extracted!')