# Hypervariorum

## Installation
- Clone this repository to your local machine.
- Cd into the repository and run `pdm install -d`.
- `raw/` is a symlink to a sibling clone of the external corpus
  [PerseusDLCode/NVS_Shakespeare](https://github.com/PerseusDLCode/NVS_Shakespeare)
  (a fork of [gregorycrane/NVS_Shakespeare](https://github.com/gregorycrane/NVS_Shakespeare)).
  It is not fetched by `pdm install`. To bootstrap it, from the
  directory containing this repository:
  ```
  git clone https://github.com/PerseusDLCode/NVS_Shakespeare.git
  ln -s ../NVS_Shakespeare nvs/raw
  ```
  (adjust the target directory name in the `ln -s` command if your
  clone of this repository is not named `nvs`).

## Contents
    - **bin**: scripts

## Processing Critical Commentary
    `make shake.var.lear.annot.xml`
    
    
