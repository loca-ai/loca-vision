#!/usr/bin/env python3
"""Interface dealing with Google Cloud."""

from google.cloud import storage
from google.cloud import vision
from typing import MutableSequence, Sequence
from requests.exceptions import ConnectionError
from slugify import slugify

from dotenv import dotenv_values
import os
import requests
from .wiki_monument import WikiMonument
from .wiki_parser import headers
from tqdm import tqdm
import hashlib
import re
import base64
import hashlib

config = {**dotenv_values(".env"), **os.environ}

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config["GOOGLE_APPLICATION_CREDENTIALS"]


def upload_images_from_monuments(
    monuments: MutableSequence[WikiMonument], bar=True
) -> MutableSequence[WikiMonument]:
    """Takes Monuments and their URLs, uploads them to Google Cloud, and replaces those URLs with the new URIs."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(config["IMAGE_BUCKET"])

    for mon in tqdm(monuments) if bar else monuments:
        for i, url in enumerate(mon.image_urls):
            if not url.startswith("gs"):
                ext = url.split(".")[-1]

                uri = f"{slugify(mon.name)}/{i}.{ext}"
                blob = bucket.blob(uri)

                try:
                    r = requests.get(url, headers=headers, timeout=3)
                    blob.upload_from_string(r.content)
                    mon.image_urls[i] = f'gs://{config["IMAGE_BUCKET"]}/{uri}'
                except ConnectionError as e:
                    print("Could not read image", url, ", skipping")

    return


def upload_base64_image(b64: str) -> str:
    """Uploads an image in base64 to the GC bucket and returns a URI pointing to the image."""
    fn = hashlib.md5(b64).hexdigest()[:15]
    uri = f"{fn}.jpeg"
    data = b64.split('base64,')[1]
    bin_data = base64.b64encode(data)
    storage_client = storage.Client()
    bucket = storage_client.bucket(config["IMAGE_BUCKET"])
    blob = bucket.blob(uri)
    blob.upload_from_string(bin_data)
    return f"gs://{config['IMAGE_BUCKET']}/{uri}"


def create_product(product_id, product_display_name):
    client = vision.ProductSearchClient()

    # A resource that represents Google Cloud Platform location.
    location_path = f"projects/{config['PROJECT_ID']}/locations/us-east1"

    # Create a product with the product specification in the region.
    # Set product display name and product category.
    product = vision.Product(
        display_name=product_display_name,
        product_category='general-v1')

    # The response is the product with the `name` field populated.
    response = client.create_product(
        parent=location_path,
        product=product,
        product_id=product_id)

    add_product_to_product_set(product_id)

    # Display the product information.
    print('Product name: {}'.format(response.name))

def create_reference_image(product_id, reference_image_id, gcs_uri):
    """Create a reference image.
    Args:
        project_id: Id of the project.
        location: A compute region name.
        product_id: Id of the product.
        reference_image_id: Id of the reference image.
        gcs_uri: Google Cloud Storage path of the input image.
    """
    client = vision.ProductSearchClient()

    # Get the full path of the product.
    product_path = client.product_path(
        project=config['PROJECT_ID'], location='us-east1', product=product_id)

    # Create a reference image.
    reference_image = vision.ReferenceImage(uri=gcs_uri)

    # The response is the reference image with `name` populated.
    image = client.create_reference_image(
        parent=product_path,
        reference_image=reference_image,
        reference_image_id=reference_image_id)

def add_product_to_product_set(product_id):
    """Add a product to a product set.
    Args:
        project_id: Id of the project.
        location: A compute region name.
        product_id: Id of the product.
        product_set_id: Id of the product set.
    """
    client = vision.ProductSearchClient()

    # Get the full path of the product set.
    product_set_path = client.product_set_path(
        project=config['PROJECT_ID'], location='us_east1',
        product_set=config['PRODUCT_SET_ID'])

    # Get the full path of the product.
    product_path = client.product_path(
        project=config['PROJECT_SET'], location='us_east1', product=product_id)

    # Add the product to the product set.
    client.add_product_to_product_set(
        name=product_set_path, product=product_path)

def monuments_to_csv(monuments: Sequence[WikiMonument]) -> str:
    """Reads the monuments into a CSV suitable for input and return it."""
    data = []
    for mon in monuments:
        for url in mon.image_urls:
            if not url.startswith("gs"):
                raise ValueError("Cannot import non-GC URL: ", url)

            product_id = re.match(
                f'gs://{config["IMAGE_BUCKET"]}' + r"/([^/ .]+)/\d+\.\w+", url
            ).group(1)
            data.append(
                [
                    url,  # image-uri
                    "",  # image-id: skip
                    config["PRODUCT_SET_ID"],  # product-set-id,
                    product_id,  # product-id: slugified name
                    "general-v1",  # product-category
                    mon.name,  # product-display-name
                    "",  # labels: skip for now
                    "",  # bounding poly: skip for now
                ]
            )

    # escape using quotes
    return "\n".join([",".join(['"' + c + '"' for c in l]) for l in data])


def import_product_sets(gcs_uri):
    """Import images of different products in the product set.
    Args:
        gcs_uri: Google Cloud Storage URI.
            Target files must be in Product Search CSV format.
    """
    client = vision.ProductSearchClient()

    # A resource that represents Google Cloud Platform location.
    location_path = f"projects/{config['PROJECT_ID']}/locations/us-east1"

    # Set the input configuration along with Google Cloud Storage URI
    gcs_source = vision.ImportProductSetsGcsSource(csv_file_uri=gcs_uri)
    input_config = vision.ImportProductSetsInputConfig(gcs_source=gcs_source)

    # Import the product sets from the input URI.
    response = client.import_product_sets(
        parent=location_path, input_config=input_config
    )

    print("Processing operation name: {}".format(response.operation.name))
    # synchronous check of operation status
    result = response.result()
    print("Processing done.")

    for i, status in enumerate(result.statuses):
        print("Status of processing line {} of the csv: {}".format(i, status))
        # Check the status of reference image
        # `0` is the code for OK in google.rpc.Code.
        if status.code == 0:
            reference_image = result.reference_images[i]
            print(reference_image)
        else:
            print("Status code not OK: {}".format(status.message))


def upload_product_set(monuments: Sequence[WikiMonument]):
    """Uploads the Monuments as a product set."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(config["CSV_BUCKET"])
    csv = monuments_to_csv(monuments)

    csv_id = hashlib.sha256(csv.encode()).hexdigest()
    blob = bucket.blob(csv_id + ".csv")

    blob.upload_from_string(csv)

    uri = f'gs://{config["CSV_BUCKET"]}/{csv_id}.csv'
    import_product_sets(uri)


def get_similar_products_file(
    b64,
    filter,
    max_results,
):
    """Search similar products to image.
    Args:
        project_id: Id of the project.
        location: A compute region name.
        product_set_id: Id of the product set.
        product_category: Category of the product.
        file_path: Local file path of the image to be searched.
        filter: Condition to be applied on the labels.
                Example for filter: (color = red OR color = blue) AND style = kids
                It will search on all products with the following labels:
                color:red AND style:kids
                color:blue AND style:kids
        max_results: The maximum number of results (matches) to return. If omitted, all results are returned.
    """
    # product_search_client is needed only for its helper methods.
    product_search_client = vision.ProductSearchClient()
    image_annotator_client = vision.ImageAnnotatorClient()

    # Read the image as a stream of bytes.
    content = base64.b64encode(b64.split['base64,'][1])

    # Create annotate image request along with product search feature.
    image = vision.Image(content=content)

    # product search specific parameters
    product_set_path = product_search_client.product_set_path(
        project='loca-346705', location='us-east-1', product_set=config['PRODUCT_SET_ID']
    )
    product_search_params = vision.ProductSearchParams(
        product_set=product_set_path,
        product_categories=['general-v1'],
        filter=filter,
    )
    image_context = vision.ImageContext(product_search_params=product_search_params)

    # Search products similar to the image.
    response = image_annotator_client.product_search(
        image, image_context=image_context, max_results=max_results
    )

    index_time = response.product_search_results.index_time
    print("Product set index time: ", end="")
    print(index_time)

    results = response.product_search_results.results

    print("Search results:")
    for result in results:
        product = result.product

        print("Score(Confidence): {}".format(result.score))
        print("Image name: {}".format(result.image))

        print("Product name: {}".format(product.name))
        print("Product display name: {}".format(product.display_name))
        print("Product description: {}\n".format(product.description))
        print("Product labels: {}\n".format(product.product_labels))

    return results
