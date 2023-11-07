# Frontend

## Requirements

If Node.js (version v18.17.1 or later) is not installed on your system, download it from https://nodejs.org/en. 

### Installation of Node.js on Linux
Extract the downloaded folder:
```
tar -xvf node-v18.17.1-linux-x64.tar.xz
```
Make its location known by extending the PATH variable in `~/.bashrc`. For example:
```
PATH="$PATH:/<path-to-folder>/node-v18.17.1-linux-x64/bin"
```
Open a new terminal and check that Node.js is available:
```
node --version   (output should be v18.17.1)
```

### Installation of Node.js on Windows

Download the installer (*.msi) and follow the installation dialog. After completion, open a Powershell and check that node is available.
```
node --version   (output should be v18.17.1)
```

## Run application

Open a terminal (on Linux) or Powershell (on Windows) and navigate to the frontend folder of this repository. 
```
cd <path-to-repository>
cd frontend
```

When running the application for the first time, install the required node packages with this command:
```
npm install
```
Start the application (for testing and development):
```
npm start
```
Wait till the compilation is complete ("webpack complied sucessfully"). Then open the app in your browser `http://localhost:3000`.

### Deploying application
You can create an optimized build of the application with the following command:
```
npm run build
```
To run the optimized build use:
```
serve -s build
```
If 'serve' is not available, install it with:
```
npm install --global serve
```

## Known issues

- Mac OS: Safari browser leads to connection problems with Python server (related to CORS). Recommended workaround: use Firefox browser on Mac OS.
- Linux: Google Chrome browser: artefacts with lasso selection in scatter plots; Firefox browser: parallel coordinates selection not working; Recommended workaround: use Chromium browser.

<!--
If there are certificate errors downloading packages during install or run use the following setting before executing meteor command.
#### Resolve in Linux
```
NODE_TLS_REJECT_UNAUTHORIZED=0 meteor <any-command>
```

#### Resolve in Windows
In standard command prompt:
```
set NODE_TLS_REJECT_UNAUTHORIZED=0
```
in Powershell use:
```
$env:NODE_TLS_REJECT_UNAUTHORIZED = "0"
```

serve cannot be run on Windows:
https://www.com-magazin.de/tipps-tricks/powershell/windows-10-verweigert-ausfuehrung-powershell-skript-2546684.html
--->