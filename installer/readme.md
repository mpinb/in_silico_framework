# Installer

The default installation method for ISF is `pixi`. However, it is convenient to keep track of older installation methods, such as the Python 2 installer, and the Anaconda-based Python3 installer.
In addition, these Anaconda-based installers allow for an offline installer: packages are tracked in the `pyx.x/downloads` subdirectories.

## Default

Installing ISF the default way (i.e. with `pixi`) can be done by first installing `pixi`:

```shell
curl -fsSL https://pixi.sh/install.sh | sh
```
and then installing ISF with pixi:
```shell
cd in_silico_framework
pixi install
```

## Anaconda/offline
Installing ISF with the Anaconda-based installer (e.g. for an offline installation) can be done by:

```shell
bash install.sh
```