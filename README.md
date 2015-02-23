# putio-downloader
Simple script to watch your [put.io] folders

parameters:

| Argument                  | example value         | Mandatory                 |
|:----------------------    |:-------------         |:----                      |
| --api_key=                | ABCD                  | yes                       |
| --number_of_connections=  | 1-10                  |no (defaults to 1)         |
| --delete_after_download=  | none                  |no (defaults to false)     |
| --output-directory=       | /media/, "C:\\Media"  |no (defaults to current directory)|
| --exclude_pattern=        | shared                |no                         |
| --days_to_keep=           | 1-30                  |no (defaults to 7)         |


example
./putio_downloader.py --api_key=ABC --output_directory="/media/" --number_of_connections=8 --exclude_pattern='items shared' --exclude_pattern='Sports'


The above will download with 8 connections, to folder /media/ and will exclude all files and folders that contain 'items shared' or 'Sports', without deleting.

[put.io]:http://put.io
