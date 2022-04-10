# loca-vision

Object recognition API for Loca

## Structure

This repo contains two distinct pieces of functionality: the interface to the Google Cloud Product
Search API that underpins the monument recognition, and the pre-population of that cloud data using
Wikipedia data.

## Secrets
To run successfully, a `.env` file and Google API credentials must be provided: see Nicholas
Miklaucic for that information.

## Installation
In this, the outer directory, run:

``` sh
pip install --editable .
```

This lets you do:

``` python
import loca_vision.gcloud

# do whatever you want!
```
