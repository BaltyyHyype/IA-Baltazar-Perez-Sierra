from bing_image_downloader import downloader

busquedas = {
    "aranas": ["spider macro", "tarantula", "arachnid", "araña cazadora"],
    "ballenas": ["whale underwater", "blue whale", "orca whale", "humpback whale jumping"],
    "monos": ["monkey in jungle", "macaque", "chimp", "wild monkey"],
    "pajaros": ["bird flying", "parrot", "eagle", "pajaro silvestre"],
    "ranas": ["frog", "poison dart frog", "rana de arbol", "wild toad"]
}

LIMITE_POR_BUSQUEDA = 2000 

for carpeta, queries in busquedas.items():
    for query in queries:
        print(f"\n--- Descargando fotos de '{query}' para la carpeta {carpeta} ---")
        downloader.download(
            query, 
            limit=LIMITE_POR_BUSQUEDA, 
            output_dir=f"dataset/{carpeta}", 
            adult_filter_off=True, 
            force_replace=False, 
            timeout=60
        )