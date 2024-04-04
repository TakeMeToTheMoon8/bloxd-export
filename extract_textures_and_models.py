import re, requests, base64, os, demjson3
from bs4 import BeautifulSoup

config = {
    'target_site': 'https://bloxd.io/',
    'target_site_cdn': 'https://bloxdcdn.bloxdhop.io/static/js/',
    'save_path': './extracted/',
}

flags = re.IGNORECASE | re.MULTILINE
regex_sites = re.compile(r"\"static/js/\"\+.\+\"\.\"\+(.*)\[.]\+\"\.chunk\.js\"", flags)
regex_names = re.compile(r'\"\./(.+?)\":([0-9]+)', flags) # Catastrophic backtracking sitting here /!\
regex_models = re.compile(r'([0-9]+):function\(.\){\"use strict\";.\.exports=\"(data:model/[^;]+;base64[^\"]+)', flags)
regex_images = re.compile(r'([0-9]+):function\(.\){\"use strict\";.\.exports=\"(data:image/[^;]+;base64[^\"]+)', flags)
site_parsed = BeautifulSoup(requests.get(config['target_site']).text, 'html.parser')

main_site_script = [sc['src'] for sc in site_parsed.find_all('script', src=True) if '/static/js/' in sc['src']][-1]
main_site_script_url = config['target_site'].removesuffix('/') + main_site_script
main_site_script_content = requests.get(main_site_script_url).text

scripts_name_match = re.findall(regex_sites, main_site_script_content)[0]
scripts_name_dict = demjson3.decode(scripts_name_match)
scripts_url_list = [f'{config["target_site_cdn"]}{str(numeric_id)}.{scripts_name_dict[numeric_id]}.chunk.js' for numeric_id in scripts_name_dict.keys()]

all_content = ''
for script_url in scripts_url_list:
    script_content = requests.get(script_url).text
    all_content += f'{script_content}\n'

names_matches = re.finditer(regex_names, all_content)
models_matches = re.finditer(regex_models, all_content)
images_matches = re.finditer(regex_images, all_content)
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
