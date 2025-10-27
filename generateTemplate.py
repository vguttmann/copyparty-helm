import re
import string
from re import sub
import os
import sys

# @TODO: Change on merge!
sys.path.append('../')
COPYPARTY_MAIN = os.getcwd() + '/../copyparty/copyparty/__main__.py'
print(COPYPARTY_MAIN)
from copyparty.copyparty.cfg import flagcats

def camelCase(s):
    # Use regular expression substitution to replace underscores and hyphens with spaces,
    # then title case the string (capitalize the first letter of each word), and remove spaces
    s = sub(r"(_|-)+", " ", s).title().replace(" ", "")
    
    # Join the string, ensuring the first letter is lowercase
    return ''.join([s[0].lower(), s[1:]])

# awk -F\" '/add_argument\("-[^-]/{print(substr($2,2))}' copyparty/__main__.py | sort | tr '\n' ' '

def parseHelp(line):
    helpOption = re.search(r'(?<=help=")[^"]*', line)
    if helpOption is not None:
        return '  # ' + helpOption[0] + '\n'
    else:
        return ''

def escapeAnsi(text):
    return re.compile(r'(?:\\x1b|\\033|\\e)', flags=re.IGNORECASE).sub('', re.compile(r'(?:\\x1b|\\033|\\e)\[[0-?]*[ -/]*[@-~]', flags=re.IGNORECASE).sub('', re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])').sub('', text)))

def parseConfig(line):
    configOption = '  ' + re.sub('-', '', line.split('"')[1]) + ':\n'
    return configOption

def getConfigKey(line):
    return re.sub('-', '', line.split('"')[1])

def parseMetavar(line):
    metavar = re.search(r'(?<=metavar=")[^"]*', line)
    if metavar is not None:
        if 'action="append"' in line:
            return '  # type: ' + metavar[0] + '\n' + '  # type: ARRAY' + '\n'
        return '  # type: ' + metavar[0] + '\n'
    elif 'store_true' in line:
        return '  # type: BOOLEAN\n'
    else:
        return ''

def parseRepeatable(line):
    if 'action="append"' in line:
        return '  # REPEATABLE: YES (use YAML array) ' + '\n'
    else:
        return ''

def parseDefault(line):
    default = re.search(r'(?<=default=")[^"]*', line)
    if default is not None:
        if default[0] == '':
            return '  # default: [empty string] \n'
        return '  # default: ' + default[0] + '\n'
    else:
        return ''

def createConfigMap():
    with open(COPYPARTY_MAIN) as copyparty:
        yamlContent = '    [global]\n'
        currentGroup = ''
        for line in copyparty.readlines():
            if 'add_argument' in line:
                if  'help sections' in line or '        ap2' in line:
                    pass
                elif 'add_argument_group' in line:
                    currentGroup = re.sub(r'\W', '_', camelCase((line.split('"')[1])))

                else:
                    entry = ''
                    parsedline = escapeAnsi(line)
                    if 'action="append"' in parsedline:
                        entry = '    {{{{- if .Values.{group}.{value} }}}}\n'.format(group=currentGroup, value=getConfigKey(line))
                        entry += '      {{{{- range .Values.{group}.{value} }}}}\n'.format(group=currentGroup, value=getConfigKey(line))
                        entry += '      {value}: {{{{ . }}}}\n'.format(value=getConfigKey(line))
                        entry += '    {{- end }}\n'
                    elif 'action="store_true"' in parsedline:
                        entry = '    {{{{- if .Values.{group}.{value} }}}}\n'.format(group=currentGroup, value=getConfigKey(line))
                        entry += '      {value}\n'.format(value=getConfigKey(line))
                        entry += '    {{- end }}\n'
                    else: 
                        entry = '    {{{{- if .Values.{group}.{value} }}}}\n'.format(group=currentGroup, value=getConfigKey(line))
                        entry += '      {value}: {{{{ .Values.{group}.{value} }}}}\n'.format(group=currentGroup, value=getConfigKey(line))
                        entry += '    {{- end }}\n'
                    yamlContent += entry
        yamlContent = """apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ include "copyparty-helm.fullname" . }}-config
  namespace: {{ .Values.namespace | .Release.namespace }}

data:
  copyparty.cfg: |
""" + yamlContent
        with open('templates/configmap.yaml', 'w') as t:
            t.write(yamlContent)

def createValuesYAML():
    with open(COPYPARTY_MAIN) as copyparty:
        yamlContent = ''
        with open('values.template.yaml') as template:
            yamlContent = template.read()           
        for line in copyparty.readlines():
            if 'add_argument' in line:
                if  'help sections' in line or '        ap2' in line:
                    pass
                elif 'add_argument_group' in line:
                    yamlContent += '\n' + re.sub(r'\W', '_', camelCase((line.split('"')[1]))) + ':\n'
                else:
                    entry = ''
                    parsedline = escapeAnsi(line)
                    entry += parseHelp(parsedline)
                    entry += parseMetavar(parsedline)
                    entry += parseDefault(parsedline)
                    entry += parseRepeatable(parsedline)
                    entry += parseConfig(parsedline)
                    
                    yamlContent += entry
        with open('values.yaml', 'w') as t:
            t.write(yamlContent)


def getVariableInfo(key):
    with open(COPYPARTY_MAIN) as copyparty:
        yamlContent = ''
        for line in copyparty.readlines():
            if 'add_argument' in line:
                if  'help sections' in line or '        ap2' in line:
                    pass
                elif 'add_argument_group' in line:
                    yamlContent += '\n' + re.sub(r'\W', '_', camelCase((line.split('"')[1]))) + ':\n'
                else:
                    if key in line:
                        entry = ''
                        parsedline = escapeAnsi(line)
                        entry += parseHelp(parsedline)
                        entry += parseMetavar(parsedline)
                        entry += parseDefault(parsedline)
                        entry += parseRepeatable(parsedline)
                        return entry
    return ''

def getVariableType(key):
    with open(COPYPARTY_MAIN) as copyparty:
        yamlContent = ''
        for line in copyparty.readlines():
            if 'add_argument' in line:
                if  'help sections' in line or '        ap2' in line:
                    pass
                elif 'add_argument_group' in line:
                    yamlContent += '\n' + re.sub(r'\W', '_', camelCase((line.split('"')[1]))) + ':\n'
                else:
                    if key in line:
                        parsedline = escapeAnsi(line)
                        if 'action="append"' in parsedline:
                            return 'ARRAY'
                        elif 'action="store_true"' in parsedline:
                            return 'BOOLEAN'
                        else:
                            return 'ARGUMENT'
    return 'NOTFOUND'

def createVolume():
    volflags = """\n\nvolumes:
  - name: volumeName1
    httpURL: /the/url/to/share/this/volume/on/
    mountPath: /the/actual/filesystem/path/
    existingClaim: ""
    storageClass: "longhorn-nvme"
    resources:
      requests:
        storage: 2Gi
      limits:
        # @TODO: Sync with vmaxb
        storage: 3Gi
    # @TODO: Move to config since copyparty can't do RWX anyway (or should not at least)
    accessModes:
      - ReadWriteOnce
    volflags:"""
    prevkey = ''
    currentkey = ''
    for key in flagcats.keys():
        volflags += "\n      " + re.sub(r'\W', '_',camelCase(re.sub('\n.*', '', key))) + ':\n'
        for l2key in flagcats[key].keys():
            prevkey = currentkey
            if '=' in l2key:
                currentkey = l2key.split('=')[0]
            else:
                currentkey = l2key
            content = escapeAnsi(flagcats[key][l2key])
            content = re.sub('\n', '', content)
            volflags += '        # ' + content + '\n'
            if '=' in l2key:
                l2key = l2key.split('=')

                volflags += '        # Example: ' + l2key[1] + '\n'
                l2key = l2key[0]
            volflags += re.sub(' {2,6}', '        ', getVariableInfo(l2key))
            if getVariableType(l2key) == 'NOTFOUND':
                volflags += '        # !!!VARIABLE TEMPLATING INFORMATION NOT FOUND IN COPYPARTY CODE!!!\n        # This is expected behavior with some options that are only available as volflags.\n        # Please input the text that should appear in the copyparty config verbatim as this key\'s value.\n        # !!!VARIABLE TEMPLATING INFORMATION NOT FOUND IN COPYPARTY CODE!!!\n'
            if prevkey != currentkey:
                volflags += '        ' + l2key + ':\n'
    with open('values.yaml', 'a') as t:
        t.write(volflags)

def createVolflagConfigMap():
    with open(COPYPARTY_MAIN) as copyparty:
        yamlContent = """    {{- range .Values.volumes }}
        [{{ .httpURL }}]
        {{ .mountPath }}
        accs:
            {{ .permissions }}
        flags:\n"""

        for key in flagcats.keys():
            outerGroup = re.sub(r'\W', '_',camelCase(re.sub('\n.*', '', key)))
            for l2key in flagcats[key].keys():
                if '=' in l2key:
                    l2key = l2key.split('=')[0]
                variableType = getVariableType(l2key)
                if variableType == 'BOOLEAN':
                    entry = '      {{{{- if .volflags.{group}.{value} }}}}\n'.format(group=outerGroup, value=l2key)
                    entry += '        {value}\n'.format(value=l2key)
                    entry += '      {{- end }}\n'
                elif variableType == 'ARRAY':
                    entry = '      {{{{- if .volflags.{group}.{value} }}}}\n'.format(group=outerGroup, value=l2key)
                    entry += '        {{{{- range .volflags.{group}.{value} }}}}\n'.format(group=outerGroup, value=l2key)
                    entry += '        {value}: {{{{ . }}}}\n'.format(value=l2key)
                    entry += '      {{- end }}\n'
                elif variableType == 'NOTFOUND':
                    entry = '      {{{{- if .volflags.{group}.{value} }}}}\n'.format(group=outerGroup, value=l2key)
                    entry += '        {{{{ .volflags.{group}.{value} }}}}\n'.format(group=outerGroup, value=l2key)
                    entry += '      {{- end }}\n'
                else:
                    entry = '      {{{{- if .volflags.{group}.{value} }}}}\n'.format(group=outerGroup, value=l2key)
                    entry += '        {value}: {{{{ .volflags.{group}.{value} }}}}\n'.format(group=outerGroup, value=l2key)
                    entry += '      {{- end }}\n'
                yamlContent += entry
        yamlContent += '    {{- end }}\n'
        with open('templates/configmap.yaml', 'a') as t:
            t.write(yamlContent)


createValuesYAML()
createConfigMap()
createVolume()
createVolflagConfigMap()
