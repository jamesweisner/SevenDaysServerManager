from lxml import etree

with open('big-stacks.txt') as file:
    targets = [item.strip() for item in file.readlines() if item[0] not in ['\n', '#']]

tree = etree.parse('items.xml')

items = tree.xpath('.//item')

for item in items:
    if item.get('name') in targets:
        prop = item.xpath('./property[@name="Stacknumber"]')
        if prop:
            prop[0].set('value', '60000')

tree.write('items-big-stacks.xml', pretty_print=True, xml_declaration=True, encoding='utf-8')
