content = open('app.py', encoding='utf-8').read()
idx = content.find('display_columns = ["Pin ID"')
print(repr(content[idx-200:idx+200]))
