#!/bin/bash

###
### Bump CPL versions consistently across all files
###

FILES=(setup.py
       caelus/version.py
       docs/source/conf.py
       etc/conda/caelus/meta.yaml
       etc/conda/conda-pkg.sh
       etc/conda/conda-pkg.bat
       etc/conda/installer/construct-template.yaml
      )

for fname in ${FILES[@]} ; do
    sed -i '' -e 's/0.0.2/0.1.0/' ${fname}
done
