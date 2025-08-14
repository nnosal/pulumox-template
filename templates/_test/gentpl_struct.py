#!/usr/bin/env uv run --script
# /// script
# dependencies = []
# ///
import os
USE_JINJA = True
# Structure..
files = [
    # Windows
    "templates/windows/_base.yaml", "templates/windows/10.yaml", "templates/windows/11.yaml",
    # Mac 2020 Era
    "templates/mac/_base.yaml", "templates/mac/11-big-sur.yaml", "templates/mac/12-monterey.yaml",
    "templates/mac/13-ventura.yaml", "templates/mac/14-sonoma.yaml", "templates/mac/15-sequoia.yaml",
    "templates/mac/26-tahoe.yaml",
    # Mac 2010 Era
    "templates/mac/_base10.yaml", "templates/mac/10.7-lion.yaml", "templates/mac/10.8-mountain-lion.yaml",
    "templates/mac/10.9-mavericks.yaml", "templates/mac/10.10-yosemite.yaml", "templates/mac/10.11-el-capitan.yaml",
    "templates/mac/10.12-sierra.yaml", "templates/mac/10.13-high-sierra.yaml",
    "templates/mac/10.14-mojave.yaml", "templates/mac/10.15-catalina.yaml",
    # Linux
    "templates/linux/_base.yaml", "templates/linux/ubuntu.yaml", "templates/linux/debian.yaml",
    "templates/linux/centos-stream.yaml", "templates/linux/linux-mint.yaml", "templates/linux/manjaro.yaml",
]
# Contenus par défaut..
content_base = """# Template: {file}
---
vmimgs:
vmtpls2:
vmtpls:
vms:
lxcimgs:
lxcs:
"""
content_extended = "#extends _base.yaml\n# Template: {file}\n---\n"
content_extended10 = "#extends _base10.yaml\n# Template: {file}\n---\n"

content_jinja_base = """# Template: {file}
---
vmimgs:
vmtpls2:
vmtpls:
vms:
lxcimgs:
lxcs:
"""
content_jinja_extended = """{{% extends "_base.yaml.j2" %}}
{{% block content %}}
# Template: {file}
---
{{% endblock %}}
"""

content_jinja_extended10 = """{{% extends "_base10.yaml.j2" %}}
{{% block content %}}
# Template: {file}
---
{{% endblock %}}
"""

# Génération...
for f in files:
    fname = f + ".j2" if USE_JINJA and not f.endswith(".j2") else f
    os.makedirs(os.path.dirname(fname), exist_ok=True)
    with open(fname, "w", encoding="utf-8") as file:
        if f.endswith("_base10.yaml"):
            file.write(content_jinja_base.format(file=fname) if USE_JINJA else content_base.format(file=fname))
        elif f.endswith("_base.yaml"):
            file.write(content_jinja_base.format(file=fname) if USE_JINJA else content_base.format(file=fname))
        elif f.startswith("templates/mac/10."):
            file.write(content_jinja_extended10.format(file=fname) if USE_JINJA else content_extended10.format(file=fname))
        else:
            file.write(content_jinja_extended.format(file=fname) if USE_JINJA else content_extended.format(file=fname))
