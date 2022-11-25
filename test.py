from ast import literal_eval

import nextcord
color = "#71368a"
k = color.replace('#', '')
col = int(k, 16)
print(nextcord.Color.dark_purple())
print(col)