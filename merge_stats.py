import os
path = r"c:\Users\user\Documents\d\e\templates\admin_stats.html"
with open(path, "w", encoding="utf-8") as f:
    f.write(open(r"c:\Users\user\Documents\d\e\templates\admin_stats_p1.tmp", "r", encoding="utf-8").read())
    f.write(open(r"c:\Users\user\Documents\d\e\templates\admin_stats_p2.tmp", "r", encoding="utf-8").read())
print("OK")
