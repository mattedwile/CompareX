import os
import json
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

import requests

from flask import (
    Flask,
    jsonify,
    request,
    render_template_string,
)

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_


# ============================================================
# COMPAREX
# COMPLETE SINGLE-FILE APPLICATION
#
# REAL REEFAPI + REAL FLIPKART DATA
# SQLITE DATABASE
# 7 CATEGORIES
# 50 PRODUCTS / CATEGORY TARGET
# ============================================================


# ============================================================
# ENVIRONMENT
# ============================================================

def load_dotenv():
    """Load basic .env settings without requiring python-dotenv."""
    env_file = Path(__file__).resolve().parent / ".env"
    if not env_file.is_file():
        return

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        os.environ.setdefault(key, value)


load_dotenv()


BASE_DIR = Path(__file__).resolve().parent


# ============================================================
# FLASK
# ============================================================

app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv(
    "COMPAREX_SECRET",
    "comparex-development-secret"
)


# ============================================================
# DATABASE
# ============================================================

# IMPORTANT:
# We deliberately use an absolute path so you can easily find
# the database beside app.py instead of wondering where SQLite
# created it.

DATABASE_FILE = BASE_DIR / "comparex.db"

app.config["SQLALCHEMY_DATABASE_URI"] = (
    "sqlite:///"
    + DATABASE_FILE.as_posix()
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# ============================================================
# REEFAPI
# ============================================================

REEF_API_KEY = os.getenv(
    "REEF_API_KEY",
    ""
).strip()

REEF_API_BASE_URL = os.getenv(
    "REEF_API_BASE_URL",
    "https://api.reefapi.com/flipkart/v1"
).strip().rstrip("/")


# ============================================================
# APPLICATION SETTINGS
# ============================================================

PRODUCT_TARGET_PER_CATEGORY = int(
    os.getenv(
        "PRODUCT_TARGET_PER_CATEGORY",
        "100"
    )
)

MAX_PAGES_PER_QUERY = int(
    os.getenv(
        "MAX_PAGES_PER_QUERY",
        "6"
    )
)

REQUEST_DELAY_SECONDS = float(
    os.getenv(
        "REQUEST_DELAY_SECONDS",
        "0.15"
    )
)


# ============================================================
# CATEGORY SEARCH STRATEGY
# ============================================================

CATEGORY_CONFIG = {

    "smartphones": {
        "name": "Smartphones",
        "queries": [
            "smartphone",
            "mobile phone",
            "android smartphone",
            "5g smartphone",
            "mobile"
        ]
    },

    "laptops": {
        "name": "Laptops",
        "queries": [
            "laptop",
            "gaming laptop",
            "thin laptop",
            "business laptop",
            "notebook"
        ]
    },

    "gpus": {
        "name": "GPUs",
        "queries": [
            "graphics card",
            "GPU",
            "RTX graphics card",
            "NVIDIA graphics card",
            "AMD graphics card"
        ]
    },

    "cpus": {
        "name": "CPUs",
        "queries": [
            "processor",
            "CPU",
            "Ryzen processor",
            "Intel processor",
            "desktop processor"
        ]
    },

    "tablets": {
        "name": "Tablets",
        "queries": [
            "tablet",
            "android tablet",
            "iPad",
            "Samsung tablet",
            "tablet PC"
        ]
    },

    "gaming-consoles": {
        "name": "Gaming Consoles",
        "queries": [
            "gaming console",
            "PlayStation",
            "Xbox",
            "Nintendo Switch",
            "game console"
        ]
    },

    "routers": {
        "name": "Routers",
        "queries": [
            "wifi router",
            "wireless router",
            "WiFi 6 router",
            "5G router",
            "network router"
        ]
    }
}


# ============================================================
# DATABASE MODELS
# ============================================================

class Category(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(120),
        nullable=False,
        unique=True
    )

    slug = db.Column(
        db.String(120),
        nullable=False,
        unique=True,
        index=True
    )

    products = db.relationship(
        "Product",
        backref="category",
        lazy=True
    )


class Brand(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(200),
        nullable=False,
        unique=True
    )

    products = db.relationship(
        "Product",
        backref="brand",
        lazy=True
    )


class DataSource(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(200),
        nullable=False,
        unique=True
    )

    base_url = db.Column(
        db.Text
    )

    source_type = db.Column(
        db.String(50),
        nullable=False,
        default="api"
    )


class Product(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    category_id = db.Column(
        db.Integer,
        db.ForeignKey("category.id"),
        nullable=False,
        index=True
    )

    brand_id = db.Column(
        db.Integer,
        db.ForeignKey("brand.id"),
        nullable=True
    )

    external_id = db.Column(
        db.String(250),
        nullable=False,
        unique=True,
        index=True
    )

    listing_id = db.Column(
        db.String(300)
    )

    itm_id = db.Column(
        db.String(200),
        index=True
    )

    name = db.Column(
        db.String(700),
        nullable=False
    )

    subtitle = db.Column(
        db.Text
    )

    model = db.Column(
        db.String(300)
    )

    image_url = db.Column(
        db.Text
    )

    product_url = db.Column(
        db.Text
    )

    description = db.Column(
        db.Text
    )

    availability = db.Column(
        db.String(100)
    )

    in_stock = db.Column(
        db.Boolean
    )

    rating = db.Column(
        db.Float
    )

    rating_count = db.Column(
        db.Integer
    )

    review_count = db.Column(
        db.Integer
    )

    vertical = db.Column(
        db.String(200)
    )

    flipkart_advantage = db.Column(
        db.Boolean
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda:
        datetime.now(timezone.utc)
    )

    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda:
        datetime.now(timezone.utc),
        onupdate=lambda:
        datetime.now(timezone.utc)
    )

    prices = db.relationship(
        "Price",
        backref="product",
        lazy=True,
        cascade="all, delete-orphan"
    )

    specifications = db.relationship(
        "ProductSpecification",
        backref="product",
        lazy=True,
        cascade="all, delete-orphan"
    )


class ProductSpecification(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("product.id"),
        nullable=False
    )

    name = db.Column(
        db.String(300),
        nullable=False
    )

    value = db.Column(
        db.Text
    )


class Price(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("product.id"),
        nullable=False
    )

    source_id = db.Column(
        db.Integer,
        db.ForeignKey("data_source.id"),
        nullable=False
    )

    price = db.Column(
        db.Numeric(14, 2)
    )

    mrp = db.Column(
        db.Numeric(14, 2)
    )

    discount_percent = db.Column(
        db.Float
    )

    currency = db.Column(
        db.String(10),
        default="INR"
    )

    availability = db.Column(
        db.String(100)
    )

    checked_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda:
        datetime.now(timezone.utc)
    )

    source = db.relationship(
        "DataSource"
    )


class PriceHistory(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("product.id"),
        nullable=False
    )

    source_id = db.Column(
        db.Integer,
        db.ForeignKey("data_source.id"),
        nullable=False
    )

    price = db.Column(
        db.Numeric(14, 2)
    )

    mrp = db.Column(
        db.Numeric(14, 2)
    )

    discount_percent = db.Column(
        db.Float
    )

    currency = db.Column(
        db.String(10),
        default="INR"
    )

    checked_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda:
        datetime.now(timezone.utc)
    )


class SyncLog(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    category_id = db.Column(
        db.Integer,
        db.ForeignKey("category.id")
    )

    source_id = db.Column(
        db.Integer,
        db.ForeignKey("data_source.id"),
        nullable=False
    )

    status = db.Column(
        db.String(50),
        nullable=False
    )

    records_processed = db.Column(
        db.Integer,
        default=0
    )

    started_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda:
        datetime.now(timezone.utc)
    )

    finished_at = db.Column(
        db.DateTime(timezone=True)
    )

    error_message = db.Column(
        db.Text
    )


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def initialize_database():

    db.create_all()

    for slug, config in CATEGORY_CONFIG.items():

        category = Category.query.filter_by(
            slug=slug
        ).first()

        if category is None:

            category = Category(
                name=config["name"],
                slug=slug
            )

            db.session.add(category)

    source = DataSource.query.filter_by(
        name="ReefAPI / Flipkart"
    ).first()

    if source is None:

        source = DataSource(
            name="ReefAPI / Flipkart",
            base_url=REEF_API_BASE_URL,
            source_type="api"
        )

        db.session.add(source)

    db.session.commit()


# ============================================================
# GENERAL HELPERS
# ============================================================

def utc_now():

    return datetime.now(
        timezone.utc
    )


def clean_text(value):

    if value is None:
        return None

    if isinstance(value, str):

        value = value.strip()

        return value or None

    return str(value).strip() or None


def parse_decimal(value):

    if value is None:
        return None

    if isinstance(value, dict):

        value = (
            value.get("amount")
            or value.get("value")
            or value.get("price")
        )

    try:

        text = str(value)

        text = text.replace(
            "₹",
            ""
        )

        text = text.replace(
            ",",
            ""
        )

        text = text.strip()

        if not text:
            return None

        return Decimal(text)

    except (
        InvalidOperation,
        ValueError,
        TypeError
    ):

        return None


def parse_float(value):

    if value is None:
        return None

    try:

        return float(value)

    except (
        ValueError,
        TypeError
    ):

        return None


def parse_int(value):

    if value is None:
        return None

    try:

        return int(value)

    except (
        ValueError,
        TypeError
    ):

        return None


def first_value(data, *keys):

    if not isinstance(
        data,
        dict
    ):
        return None

    for key in keys:

        if key in data:

            value = data[key]

            if value is not None:

                if isinstance(
                    value,
                    str
                ):

                    if value.strip():
                        return value

                elif value != "":

                    return value

    return None


def result_rows(payload):

    if not isinstance(
        payload,
        dict
    ):
        return []

    data = payload.get(
        "data"
    )

    if isinstance(
        data,
        dict
    ):

        results = data.get(
            "results"
        )

        if isinstance(
            results,
            list
        ):
            return results

    results = payload.get(
        "results"
    )

    if isinstance(
        results,
        list
    ):
        return results

    return []


def response_data(payload):

    data = payload.get(
        "data"
    )

    if isinstance(
        data,
        dict
    ):
        return data

    return {}


# ============================================================
# REEFAPI
# ============================================================

def reef_headers():

    if not REEF_API_KEY:

        raise RuntimeError(
            "REEF_API_KEY is missing. "
            "Create a .env file beside app.py."
        )

    return {
        "x-api-key": REEF_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }


def reef_post(
    action,
    payload
):

    url = (
        REEF_API_BASE_URL
        + "/"
        + action.lstrip("/")
    )

    try:

        response = requests.post(
            url,
            headers=reef_headers(),
            json=payload,
            timeout=60
        )

    except requests.RequestException as exc:

        raise RuntimeError(
            f"ReefAPI network error: {exc}"
        )

    try:

        body = response.json()

    except ValueError:

        raise RuntimeError(
            "ReefAPI returned non-JSON data. "
            f"HTTP {response.status_code}"
        )

    if response.status_code >= 400:

        error = body.get(
            "error"
        )

        if isinstance(
            error,
            dict
        ):

            message = (
                error.get("message")
                or
                error.get("code")
                or
                str(error)
            )

        else:

            message = str(
                error or body
            )

        raise RuntimeError(
            f"ReefAPI HTTP "
            f"{response.status_code}: "
            f"{message}"
        )

    if body.get(
        "ok"
    ) is False:

        error = body.get(
            "error"
        )

        if isinstance(
            error,
            dict
        ):

            message = (
                error.get("message")
                or
                error.get("code")
                or
                str(error)
            )

        else:

            message = str(
                error or body
            )

        raise RuntimeError(
            f"ReefAPI error: {message}"
        )

    return body


def reef_search(
    query,
    page=1
):

    return reef_post(
        "search",
        {
            "q": query,
            "page": page
        }
    )


def reef_product(
    product_url=None,
    itm_id=None
):

    payload = {}

    if product_url:

        payload["url"] = product_url

    elif itm_id:

        payload["itm_id"] = itm_id

    else:

        raise RuntimeError(
            "A product URL or itm_id is required."
        )

    return reef_post(
        "product",
        payload
    )


# ============================================================
# BRAND
# ============================================================

def get_or_create_brand(
    brand_name
):

    brand_name = clean_text(
        brand_name
    )

    if not brand_name:

        brand_name = "Unknown"

    brand = Brand.query.filter_by(
        name=brand_name
    ).first()

    if brand is None:

        brand = Brand(
            name=brand_name
        )

        db.session.add(
            brand
        )

        db.session.flush()

    return brand


# ============================================================
# IMAGE EXTRACTION
# ============================================================

def extract_image(row):

    image = first_value(
        row,
        "image",
        "image_url",
        "thumbnail"
    )

    if image:
        return clean_text(image)

    images = row.get(
        "images"
    )

    if isinstance(
        images,
        list
    ):

        for image in images:

            if isinstance(
                image,
                str
            ) and image.strip():

                return image.strip()

            if isinstance(
                image,
                dict
            ):

                candidate = first_value(
                    image,
                    "url",
                    "src",
                    "image"
                )

                if candidate:

                    return clean_text(
                        candidate
                    )

    return None


# ============================================================
# SAVE PRODUCT
# ============================================================

def save_product(
    row,
    category,
    source
):

    if not isinstance(
        row,
        dict
    ):
        return None

    external_id = first_value(
        row,
        "product_id",
        "fsn",
        "id"
    )

    if not external_id:

        return None

    external_id = str(
        external_id
    ).strip()

    title = first_value(
        row,
        "title",
        "name",
        "product_name"
    )

    if not title:

        return None

    title = str(
        title
    ).strip()

    product = Product.query.filter_by(
        external_id=external_id
    ).first()

    brand_name = first_value(
        row,
        "brand",
        "brand_name"
    )

    if isinstance(
        brand_name,
        dict
    ):

        brand_name = first_value(
            brand_name,
            "name"
        )

    brand = get_or_create_brand(
        brand_name
    )

    if product is None:

        product = Product(
            external_id=external_id,
            category_id=category.id,
            brand_id=brand.id,
            name=title
        )

        db.session.add(
            product
        )

        db.session.flush()

    else:

        product.category_id = (
            category.id
        )

        product.brand_id = (
            brand.id
        )

        product.name = title

    product.listing_id = clean_text(
        first_value(
            row,
            "listing_id"
        )
    )

    product.itm_id = clean_text(
        first_value(
            row,
            "itm_id"
        )
    )

    product.subtitle = clean_text(
        first_value(
            row,
            "subtitle"
        )
    )

    product.model = clean_text(
        first_value(
            row,
            "model",
            "model_name"
        )
    )

    product.image_url = extract_image(
        row
    )

    product.product_url = clean_text(
        first_value(
            row,
            "url",
            "product_url"
        )
    )

    product.description = clean_text(
        first_value(
            row,
            "description"
        )
    )

    product.availability = clean_text(
        first_value(
            row,
            "availability",
            "availability_status"
        )
    )

    in_stock = first_value(
        row,
        "in_stock"
    )

    if in_stock is not None:

        product.in_stock = bool(
            in_stock
        )

    product.rating = parse_float(
        first_value(
            row,
            "rating",
            "avg_rating"
        )
    )

    product.rating_count = parse_int(
        first_value(
            row,
            "rating_count",
            "ratings_count"
        )
    )

    product.review_count = parse_int(
        first_value(
            row,
            "review_count",
            "reviews_count"
        )
    )

    product.vertical = clean_text(
        first_value(
            row,
            "vertical"
        )
    )

    advantage = first_value(
        row,
        "flipkart_advantage"
    )

    if advantage is not None:

        product.flipkart_advantage = bool(
            advantage
        )

    # --------------------------------------------------------
    # PRICE
    # --------------------------------------------------------

    current_price = parse_decimal(
        first_value(
            row,
            "price",
            "selling_price",
            "current_price"
        )
    )

    mrp = parse_decimal(
        first_value(
            row,
            "mrp",
            "maximum_retail_price"
        )
    )

    discount = parse_float(
        first_value(
            row,
            "discount_percent"
        )
    )

    if (
        discount is None
        and current_price is not None
        and mrp is not None
        and mrp > 0
    ):

        discount = round(
            (
                (
                    float(mrp)
                    -
                    float(current_price)
                )
                /
                float(mrp)
            )
            * 100,
            2
        )

    if current_price is not None:

        now = utc_now()

        price = Price(
            product_id=product.id,
            source_id=source.id,
            price=current_price,
            mrp=mrp,
            discount_percent=discount,
            currency="INR",
            availability=product.availability,
            checked_at=now
        )

        db.session.add(
            price
        )

        history = PriceHistory(
            product_id=product.id,
            source_id=source.id,
            price=current_price,
            mrp=mrp,
            discount_percent=discount,
            currency="INR",
            checked_at=now
        )

        db.session.add(
            history
        )

    # --------------------------------------------------------
    # KEY SPECS
    # --------------------------------------------------------

    specs = row.get(
        "key_specs"
    )

    if isinstance(
        specs,
        list
    ):

        # Do not create endless duplicate specs.
        existing_specs = {
            (
                spec.name,
                spec.value
            )
            for spec in product.specifications
        }

        for index, spec in enumerate(
            specs,
            start=1
        ):

            if isinstance(
                spec,
                dict
            ):

                spec_name = (
                    first_value(
                        spec,
                        "name",
                        "key"
                    )
                    or
                    f"Specification {index}"
                )

                spec_value = (
                    first_value(
                        spec,
                        "value"
                    )
                    or
                    str(spec)
                )

            else:

                spec_name = (
                    f"Specification {index}"
                )

                spec_value = str(
                    spec
                )

            spec_name = clean_text(
                spec_name
            )

            spec_value = clean_text(
                spec_value
            )

            if not spec_name:
                continue

            if not spec_value:
                continue

            pair = (
                spec_name,
                spec_value
            )

            if pair in existing_specs:
                continue

            db.session.add(
                ProductSpecification(
                    product_id=product.id,
                    name=spec_name,
                    value=spec_value
                )
            )

            existing_specs.add(
                pair
            )

    return product


# ============================================================
# CATEGORY MATCHING
# ============================================================

def row_belongs_to_category(
    row,
    category_slug
):

    config = CATEGORY_CONFIG[
        category_slug
    ]

    category_name = config[
        "name"
    ].lower()

    analytics = row.get(
        "analytics"
    )

    if isinstance(
        analytics,
        dict
    ):

        fields = [
            analytics.get("category"),
            analytics.get("subCategory"),
            analytics.get("superCategory"),
            analytics.get("vertical")
        ]

        combined = " ".join(
            str(x).lower()
            for x in fields
            if x
        )

        if category_slug == "smartphones":

            return (
                "mobile" in combined
                or
                "phone" in combined
                or
                "smartphone" in combined
            )

        if category_slug == "laptops":

            return (
                "laptop" in combined
                or
                "notebook" in combined
            )

        if category_slug == "gpus":

            return (
                "graphic" in combined
                or
                "gpu" in combined
                or
                "computer" in combined
                and
                any(
                    x in str(
                        row.get(
                            "title",
                            ""
                        )
                    ).lower()
                    for x in [
                        "rtx",
                        "gtx",
                        "radeon",
                        "graphics"
                    ]
                )
            )

        if category_slug == "cpus":

            return (
                "processor" in combined
                or
                "cpu" in combined
                or
                any(
                    x in str(
                        row.get(
                            "title",
                            ""
                        )
                    ).lower()
                    for x in [
                        "ryzen",
                        "intel core",
                        "processor"
                    ]
                )
            )

        if category_slug == "tablets":

            return (
                "tablet" in combined
                or
                "ipad" in combined
            )

        if category_slug == "gaming-consoles":

            return (
                "gaming" in combined
                or
                "console" in combined
            )

        if category_slug == "routers":

            return (
                "router" in combined
                or
                "network" in combined
            )

    title = str(
        row.get(
            "title",
            ""
        )
    ).lower()

    if category_slug == "smartphones":

        return any(
            x in title
            for x in [
                "iphone",
                "galaxy",
                "pixel",
                "oneplus",
                "redmi",
                "realme",
                "oppo",
                "vivo",
                "motorola",
                "nothing phone",
                "smartphone"
            ]
        )

    if category_slug == "laptops":

        return (
            "laptop" in title
            or
            "notebook" in title
        )

    if category_slug == "gpus":

        return any(
            x in title
            for x in [
                "rtx",
                "gtx",
                "radeon",
                "graphics card",
                "gpu"
            ]
        )

    if category_slug == "cpus":

        return any(
            x in title
            for x in [
                "ryzen",
                "intel core",
                "core i3",
                "core i5",
                "core i7",
                "core i9",
                "processor"
            ]
        )

    if category_slug == "tablets":

        return (
            "tablet" in title
            or
            "ipad" in title
        )

    if category_slug == "gaming-consoles":

        return any(
            x in title
            for x in [
                "playstation",
                "ps5",
                "ps4",
                "xbox",
                "nintendo switch",
                "gaming console",
                "game console"
            ]
        )

    if category_slug == "routers":

        return (
            "router" in title
            or
            "wifi router" in title
            or
            "wi-fi router" in title
        )

    return category_name in title


# ============================================================
# SYNC ONE CATEGORY
# ============================================================

def sync_category(
    category_slug,
    target=None
):

    if target is None:

        target = PRODUCT_TARGET_PER_CATEGORY

    target = max(
        25,
        int(target)
    )

    if category_slug not in CATEGORY_CONFIG:

        raise RuntimeError(
            f"Unknown category: "
            f"{category_slug}"
        )

    category = Category.query.filter_by(
        slug=category_slug
    ).first()

    if category is None:

        raise RuntimeError(
            "Database category missing."
        )

    source = DataSource.query.filter_by(
        name="ReefAPI / Flipkart"
    ).first()

    existing_count = Product.query.filter_by(
        category_id=category.id
    ).count()

    # --------------------------------------------------------
    # LOG
    # --------------------------------------------------------

    log = SyncLog(
        category_id=category.id,
        source_id=source.id,
        status="running",
        records_processed=0,
        started_at=utc_now()
    )

    db.session.add(
        log
    )

    db.session.commit()

    processed = 0
    calls = 0

    try:

        # ----------------------------------------------------
        # We use several search queries.
        #
        # This is intentional because ReefAPI says repeated
        # searches are not guaranteed to return the exact same
        # ranking/results. We therefore deduplicate by
        # product_id.
        # ----------------------------------------------------

        for search_query in CATEGORY_CONFIG[
            category_slug
        ]["queries"]:

            if (
                existing_count
                +
                processed
                >= target
            ):

                break

            for page in range(
                1,
                MAX_PAGES_PER_QUERY + 1
            ):

                if (
                    existing_count
                    +
                    processed
                    >= target
                ):

                    break

                payload = reef_search(
                    search_query,
                    page
                )

                calls += 1

                rows = result_rows(
                    payload
                )

                if not rows:

                    break

                new_this_page = 0

                for row in rows:

                    if not row_belongs_to_category(
                        row,
                        category_slug
                    ):

                        continue

                    external_id = first_value(
                        row,
                        "product_id",
                        "fsn",
                        "id"
                    )

                    if not external_id:
                        continue

                    external_id = str(
                        external_id
                    ).strip()

                    already = Product.query.filter_by(
                        external_id=external_id
                    ).first()

                    if already is not None:

                        # If product exists but is in another
                        # category, don't duplicate it.
                        # Update the existing record's category.
                        already.category_id = (
                            category.id
                        )

                        continue

                    product = save_product(
                        row,
                        category,
                        source
                    )

                    if product:

                        processed += 1
                        new_this_page += 1

                    if (
                        existing_count
                        +
                        processed
                        >= target
                    ):

                        break

                db.session.commit()

                log.records_processed = (
                    processed
                )

                db.session.commit()

                # ------------------------------------------------
                # If the API tells us there is no more data,
                # stop this query.
                # ------------------------------------------------

                data = response_data(
                    payload
                )

                has_more = data.get(
                    "has_more"
                )

                next_page = data.get(
                    "next_page"
                )

                if has_more is False:

                    break

                if (
                    next_page is None
                    and
                    len(rows) < 24
                ):

                    break

                # If a page gave nothing new, still continue to
                # the next search query rather than looping forever.
                if (
                    new_this_page == 0
                    and
                    page >= 2
                ):

                    break

                time.sleep(
                    REQUEST_DELAY_SECONDS
                )

        final_count = Product.query.filter_by(
            category_id=category.id
        ).count()

        if final_count >= target:

            log.status = "success"

        else:

            log.status = "partial"

        log.records_processed = (
            processed
        )

        log.finished_at = utc_now()

        db.session.commit()

        return {
            "category": category_slug,
            "name": category.name,
            "target": target,
            "before": existing_count,
            "added": processed,
            "total": final_count,
            "api_calls": calls,
            "complete":
                final_count >= target
        }

    except Exception as exc:

        db.session.rollback()

        log.status = "failed"

        log.records_processed = (
            processed
        )

        log.finished_at = utc_now()

        log.error_message = str(
            exc
        )

        db.session.add(
            log
        )

        db.session.commit()

        raise


# ============================================================
# SYNC ALL CATEGORIES
# ============================================================

def sync_all_categories(
    target=None
):

    if target is None:

        target = PRODUCT_TARGET_PER_CATEGORY

    results = {}

    for slug in CATEGORY_CONFIG:

        try:

            results[slug] = sync_category(
                slug,
                target
            )

        except Exception as exc:

            results[slug] = {
                "category": slug,
                "complete": False,
                "error": str(exc)
            }

    return results


# ============================================================
# LATEST PRICE
# ============================================================

def latest_price(
    product
):

    prices = product.prices

    if not prices:

        return None

    return max(
        prices,
        key=lambda x:
        x.checked_at
        or datetime.min.replace(
            tzinfo=timezone.utc
        )
    )


# ============================================================
# JSON PRODUCT
# ============================================================

def product_json(
    product
):

    price = latest_price(
        product
    )

    return {
        "id": product.id,
        "external_id": product.external_id,
        "name": product.name,
        "brand":
            product.brand.name
            if product.brand
            else "Unknown",
        "category":
            product.category.name
            if product.category
            else "",
        "image":
            product.image_url,
        "url":
            product.product_url,
        "rating":
            product.rating,
        "rating_count":
            product.rating_count,
        "review_count":
            product.review_count,
        "availability":
            product.availability,
        "in_stock":
            product.in_stock,
        "price":
            float(price.price)
            if price
            and price.price is not None
            else None,
        "mrp":
            float(price.mrp)
            if price
            and price.mrp is not None
            else None,
        "discount":
            price.discount_percent
            if price
            else None
    }


# ============================================================
# HTML
# ============================================================

PAGE = """
<!DOCTYPE html>

<html lang="en">

<head>

<meta charset="UTF-8">

<meta
name="viewport"
content="width=device-width, initial-scale=1.0"
>

<title>
{{ title }}
</title>

<style>

:root {

    --bg: #070707;
    --panel: #111111;
    --panel2: #151515;
    --border: #292929;
    --text: #f5f5f5;
    --muted: #929292;
    --accent: #d7ff38;
    --danger: #ff5d5d;
    --success: #7dff91;

}

* {

    box-sizing: border-box;

}

body {

    margin: 0;

    background:
        radial-gradient(
            circle at top right,
            #191d0b 0,
            #070707 38%
        );

    color: var(--text);

    font-family:
        Inter,
        Arial,
        Helvetica,
        sans-serif;

}

a {

    color: inherit;
    text-decoration: none;

}

button,
input,
select {

    font: inherit;

}

button {

    cursor: pointer;

}

.nav {

    height: 72px;

    position: sticky;

    top: 0;

    z-index: 50;

    display: flex;

    align-items: center;

    justify-content: space-between;

    padding:
        0
        5%;

    background:
        rgba(7,7,7,.94);

    backdrop-filter:
        blur(15px);

    border-bottom:
        1px solid var(--border);

}

.logo {

    font-size: 28px;

    font-weight: 950;

    letter-spacing: -1.5px;

}

.logo span {

    color: var(--accent);

}

.navlinks {

    display: flex;

    gap: 25px;

    color: var(--muted);

}

.navlinks a:hover {

    color: white;

}

.container {

    width: min(
        1240px,
        calc(100% - 40px)
    );

    margin: auto;

    padding:
        55px
        0;

}

.hero {

    width: min(
        1100px,
        calc(100% - 40px)
    );

    margin: auto;

    padding:
        90px
        0
        75px;

}

.eyebrow {

    color: var(--accent);

    font-size: 11px;

    font-weight: 900;

    letter-spacing: 2px;

}

h1 {

    margin:
        18px
        0;

    font-size:
        clamp(
            48px,
            8vw,
            92px
        );

    line-height: .92;

    letter-spacing: -6px;

}

h2 {

    font-size: 44px;

    line-height: 1;

    letter-spacing: -3px;

}

h3 {

    margin:
        7px
        0;

}

.muted {

    color: var(--muted);

}

.hero-text {

    max-width: 690px;

    font-size: 18px;

    line-height: 1.7;

}

.search {

    display: flex;

    max-width: 820px;

    margin-top: 32px;

}

.search input {

    flex: 1;

    min-width: 0;

    padding: 17px 18px;

    color: white;

    background: #111;

    border:
        1px solid
        #333;

    outline: none;

    border-radius:
        10px
        0
        0
        10px;

}

.search input:focus {

    border-color:
        var(--accent);

}

.search button {

    border: 0;

    padding:
        0
        27px;

    background:
        var(--accent);

    color: #000;

    font-weight: 950;

    border-radius:
        0
        10px
        10px
        0;

}

.stats {

    display: grid;

    grid-template-columns:
        repeat(
            4,
            1fr
        );

    gap: 13px;

    margin:
        35px
        0;

}

.stat {

    padding: 22px;

    border:
        1px solid
        var(--border);

    border-radius: 14px;

    background:
        linear-gradient(
            145deg,
            #151515,
            #0d0d0d
        );

}

.stat-number {

    font-size: 32px;

    font-weight: 950;

}

.stat-label {

    color: var(--muted);

    margin-top: 5px;

    font-size: 13px;

}

.grid {

    display: grid;

    grid-template-columns:
        repeat(
            4,
            minmax(0,1fr)
        );

    gap: 16px;

}

.card {

    overflow: hidden;

    background: var(--panel);

    border:
        1px solid
        var(--border);

    border-radius: 15px;

    transition:
        transform .2s,
        border-color .2s;

}

.card:hover {

    transform:
        translateY(-3px);

    border-color:
        #555;

}

.card-image {

    width: 100%;

    height: 230px;

    display: block;

    object-fit: contain;

    background: white;

}

.no-image {

    height: 230px;

    display: grid;

    place-items: center;

    color: #666;

    background: #151515;

}

.card-body {

    padding: 17px;

}

.card-title {

    min-height: 50px;

    line-height: 1.35;

    font-size: 15px;

    font-weight: 800;

}

.card-meta {

    margin-top: 7px;

    color: var(--muted);

    font-size: 12px;

}

.price {

    margin-top: 13px;

    font-size: 23px;

    font-weight: 950;

}

.mrp {

    color: #777;

    text-decoration:
        line-through;

    margin-left: 8px;

    font-size: 13px;

    font-weight: normal;

}

.discount {

    color:
        var(--success);

    font-size: 12px;

    margin-left: 7px;

}

.actions {

    display: flex;

    gap: 7px;

    margin-top: 15px;

}

.action {

    padding:
        8px
        11px;

    border:
        1px solid
        #333;

    border-radius: 8px;

    font-size: 12px;

}

.action:hover {

    border-color:
        #666;

}

.primary {

    display: inline-flex;

    align-items: center;

    justify-content: center;

    padding:
        13px
        17px;

    border: 0;

    border-radius: 9px;

    background:
        var(--accent);

    color: #000;

    font-weight: 950;

}

.secondary {

    display: inline-flex;

    align-items: center;

    justify-content: center;

    padding:
        13px
        17px;

    border:
        1px solid
        #3b3b3b;

    border-radius: 9px;

    background: #111;

    color: white;

    font-weight: 800;

}

.category-card {

    padding: 27px;

    border:
        1px solid
        var(--border);

    border-radius: 15px;

    background:
        linear-gradient(
            145deg,
            #151515,
            #0e0e0e
        );

}

.category-card:hover {

    border-color:
        #666;

}

.toolbar {

    display: flex;

    gap: 10px;

    flex-wrap: wrap;

    align-items: center;

    margin:
        25px
        0;

}

.pill {

    padding:
        8px
        11px;

    border:
        1px solid
        #333;

    border-radius: 100px;

    color: var(--muted);

    font-size: 12px;

}

.detail {

    display: grid;

    grid-template-columns:
        minmax(0,1fr)
        minmax(0,1fr);

    gap: 55px;

}

.detail-image {

    width: 100%;

    height: 550px;

    object-fit: contain;

    background: white;

    border-radius: 16px;

}

.detail-content {

    padding-top: 25px;

}

.detail-title {

    font-size:
        clamp(
            38px,
            5vw,
            65px
        );

    letter-spacing:
        -3px;

    line-height:
        1;

}

.big-price {

    margin:
        25px
        0;

    font-size: 40px;

    font-weight: 950;

}

.rating {

    display: inline-block;

    padding:
        7px
        10px;

    border-radius: 8px;

    background: #20250d;

    color: var(--accent);

    font-weight: 900;

}

.compare-picker {

    display: grid;

    grid-template-columns:
        1fr
        55px
        1fr;

    gap: 13px;

    align-items: end;

}

.picker {

    position: relative;

}

.picker label {

    display: block;

    margin-bottom: 7px;

    color: #aaa;

    font-size: 11px;

    font-weight: 900;

    letter-spacing: 1px;

}

.picker input {

    width: 100%;

    padding: 15px;

    background: #111;

    color: white;

    border:
        1px solid
        #333;

    border-radius: 9px;

    outline: none;

}

.suggestions {

    position: absolute;

    left: 0;

    right: 0;

    top: 73px;

    z-index: 30;

    background: #191919;

    border:
        1px solid
        #333;

    border-radius: 9px;

    overflow: hidden;

}

.suggestion {

    width: 100%;

    padding: 13px;

    text-align: left;

    color: white;

    background: #191919;

    border: 0;

    border-bottom:
        1px solid
        #292929;

}

.suggestion:hover {

    background: #252525;

}

.suggestion small {

    display: block;

    margin-top: 4px;

    color: #777;

}

.vs {

    text-align: center;

    padding-bottom: 16px;

    color: var(--accent);

    font-weight: 950;

}

.compare-table {

    margin-top: 35px;

    overflow: hidden;

    border:
        1px solid
        var(--border);

    border-radius: 15px;

}

.compare-row {

    display: grid;

    grid-template-columns:
        1fr
        1fr
        1fr;

    border-bottom:
        1px solid
        var(--border);

}

.compare-row:last-child {

    border-bottom: 0;

}

.compare-row > div {

    padding: 16px;

    border-right:
        1px solid
        var(--border);

}

.compare-row > div:last-child {

    border-right: 0;

}

.compare-head {

    background: #171717;

    font-weight: 900;

}

.spec {

    margin-top: 12px;

    padding: 14px;

    background: #121212;

    border:
        1px solid
        #252525;

    border-radius: 10px;

}

.sync-panel {

    padding: 25px;

    margin:
        30px
        0;

    border:
        1px solid
        #353535;

    border-radius: 15px;

    background:
        linear-gradient(
            145deg,
            #161616,
            #0d0d0d
        );

}

.sync-grid {

    display: grid;

    grid-template-columns:
        repeat(
            2,
            1fr
        );

    gap: 12px;

}

.sync-row {

    display: flex;

    align-items: center;

    justify-content: space-between;

    padding: 13px 15px;

    background: #111;

    border:
        1px solid
        #282828;

    border-radius: 9px;

}

.ok {

    color:
        var(--success);

}

.bad {

    color:
        var(--danger);

}

footer {

    margin-top: 70px;

    padding:
        40px
        5%;

    color: #666;

    border-top:
        1px solid
        var(--border);

}

.empty {

    padding:
        70px
        20px;

    text-align: center;

    border:
        1px dashed
        #333;

    border-radius: 15px;

    color: var(--muted);

}

@media(max-width:1000px) {

    .grid {

        grid-template-columns:
            repeat(
                2,
                minmax(0,1fr)
            );

    }

    .stats {

        grid-template-columns:
            repeat(
                2,
                1fr
            );

    }

    .detail {

        grid-template-columns:
            1fr;

    }

}

@media(max-width:650px) {

    .navlinks {

        gap: 10px;

        font-size: 13px;

    }

    .container {

        width:
            calc(100% - 28px);

    }

    .hero {

        width:
            calc(100% - 28px);

        padding-top: 55px;

    }

    h1 {

        letter-spacing:
            -3px;

    }

    .grid {

        grid-template-columns:
            1fr;

    }

    .stats {

        grid-template-columns:
            1fr 1fr;

    }

    .compare-picker {

        grid-template-columns:
            1fr;

    }

    .vs {

        padding: 0;

    }

    .sync-grid {

        grid-template-columns:
            1fr;

    }

    .search button {

        padding:
            0
            17px;

    }

}

.verdict-card{margin-top:30px;padding:28px;border:1px solid var(--accent);border-radius:18px;background:linear-gradient(135deg,#151b08,#101010)}.verdict-title{font-size:28px;font-weight:900;margin:8px 0 12px}.verdict-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:18px}.verdict-box{padding:18px;border:1px solid #292929;border-radius:14px;background:#0b0b0b}.verdict-winner{border-color:var(--accent)}.lucky-card{margin-top:24px;padding:28px;border:1px solid var(--border);border-radius:18px;background:#101010}.wheel-wrap{display:grid;place-items:center;margin:25px 0 18px}.wheel-pointer{width:0;height:0;border-left:12px solid transparent;border-right:12px solid transparent;border-top:22px solid var(--accent);margin-bottom:-8px;z-index:2}.wheel{width:230px;height:230px;border-radius:50%;border:8px solid #222;background:conic-gradient(var(--accent) 0 50%,#252525 50% 100%);position:relative;transition:transform 3s cubic-bezier(.12,.8,.18,1)}.wheel::before{content:"A                 B";white-space:pre;position:absolute;inset:0;display:grid;place-items:center;font-size:20px;font-weight:900;color:#000}.lucky-result{text-align:center;min-height:50px;padding:15px;border-radius:12px;background:#0b0b0b;border:1px solid #292929}@media(max-width:650px){.verdict-grid{grid-template-columns:1fr}.wheel{width:190px;height:190px}}
</style>

</head>


<body>


<header class="nav">

<a
href="/"
class="logo"
>
Compare<span>X</span>
</a>

<nav class="navlinks">

<a href="/">
Home
</a>

<a href="/products">
Products
</a>

<a href="/compare">
Compare
</a>

<a href="/admin">
Database
</a>

</nav>

</header>


{{ content|safe }}


<footer>

CompareX
<br>

<span class="muted">
Real product data • ReefAPI • SQLite
</span>

</footer>


</body>

</html>
"""


# ============================================================
# HOME
# ============================================================

@app.get("/")
def home():

    categories = []

    for slug, config in CATEGORY_CONFIG.items():

        category = Category.query.filter_by(
            slug=slug
        ).first()

        count = 0

        if category:

            count = Product.query.filter_by(
                category_id=category.id
            ).count()

        categories.append(
            {
                "slug": slug,
                "name": config["name"],
                "count": count
            }
        )

    total = Product.query.count()

    html = """

<section class="hero">

<div class="eyebrow">
COMPAREX / REAL MARKET DATA
</div>

<h1>
Compare smarter.
<br>
<span class="muted">
Buy better.
</span>
</h1>

<p class="hero-text muted">

A real product comparison platform
powered by your ReefAPI connection,
with products and prices stored in
your own local database.

</p>

<form
class="search"
action="/products"
method="get"
>

<input
name="q"
placeholder="Search iPhone, laptop, RTX, Ryzen..."
>

<button>
SEARCH
</button>

</form>

<div class="stats">

<div class="stat">

<div class="stat-number">
"""

    html += str(total)

    html += """

</div>

<div class="stat-label">
Products in database
</div>

</div>


<div class="stat">

<div class="stat-number">
7
</div>

<div class="stat-label">
Categories
</div>

</div>


<div class="stat">

<div class="stat-number">
"""

    html += str(
        PRODUCT_TARGET_PER_CATEGORY
    )

    html += """

+</div>

<div class="stat-label">
Target / category
</div>

</div>


<div class="stat">

<div class="stat-number">
"""

    html += (
        "YES"
        if REEF_API_KEY
        else
        "NO"
    )

    html += """

</div>

<div class="stat-label">
ReefAPI configured
</div>

</div>

</div>

"""

    if not REEF_API_KEY:

        html += """

<div class="sync-panel">

<div class="eyebrow">
ACTION REQUIRED
</div>

<h3>
ReefAPI key not configured
</h3>

<p class="muted">
Create a .env file beside app.py and add
your real REEF_API_KEY.
</p>

</div>

"""

    else:

        html += """

<div class="sync-panel">

<div class="eyebrow">
DATABASE
</div>

<h3>
Populate your database
</h3>

<p class="muted">
The database currently contains real products
returned by ReefAPI. Use the Database page
to populate missing categories.
</p>

<a
class="primary"
href="/admin"
>
OPEN DATABASE
</a>

</div>

"""

    html += """

<section>

<div class="eyebrow">
EXPLORE
</div>

<h2>
Categories
</h2>

<div class="grid">

"""

    for index, category in enumerate(
        categories,
        start=1
    ):

        html += f"""

<a
class="category-card"
href="/products?category={category['slug']}"
>

<div class="eyebrow">
{index:02d}
</div>

<h3>
{category['name']}
</h3>

<p class="muted">
{category['count']} products
stored
</p>

</a>

"""

    html += """

</div>

</section>

</section>

"""

    return render_template_string(
        PAGE,
        title="CompareX",
        content=html
    )


# ============================================================
# PRODUCTS
# ============================================================

@app.get("/products")
def products():

    q = request.args.get(
        "q",
        ""
    ).strip()

    category_slug = request.args.get(
        "category",
        ""
    ).strip()

    page = max(
        1,
        request.args.get(
            "page",
            1,
            type=int
        )
    )

    per_page = 40

    query = Product.query

    if q:

        like = f"%{q}%"

        query = query.filter(
            or_(
                Product.name.ilike(
                    like
                ),
                Product.model.ilike(
                    like
                ),
                Product.external_id.ilike(
                    like
                )
            )
        )

    if category_slug:

        query = (
            query
            .join(Category)
            .filter(
                Category.slug
                ==
                category_slug
            )
        )

    pagination = (
        query
        .order_by(
            Product.updated_at.desc()
        )
        .paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
    )

    products_list = pagination.items

    html = """

<section class="container">

<div class="eyebrow">
CATALOG
</div>

<h2>
Products
</h2>

<form
class="search"
method="get"
>

<input
name="q"
value="{{ q }}"
placeholder="Search database..."
>

"""

    if category_slug:

        html += f"""

<input
type="hidden"
name="category"
value="{category_slug}"
>

"""

    html += """

<button>
SEARCH
</button>

</form>

<div class="toolbar">

<span class="pill">
"""

    html += str(
        pagination.total
    )

    html += """
 results
</span>

"""

    for slug, config in CATEGORY_CONFIG.items():

        html += f"""

<a
class="pill"
href="/products?category={slug}"
>
{config["name"]}
</a>

"""

    html += """

</div>

"""

    if not products_list:

        html += """

<div class="empty">

<h3>
No products in the database yet.
</h3>

<p>
Open the Database page and run the
real ReefAPI sync.
</p>

<a
class="primary"
href="/admin"
>
OPEN DATABASE
</a>

</div>

"""

    else:

        html += """

<div class="grid">

"""

        for product in products_list:

            price = latest_price(
                product
            )

            if (
                price
                and
                price.price is not None
            ):

                price_html = (
                    "₹"
                    +
                    f"{float(price.price):,.0f}"
                )

                if (
                    price.mrp
                    and
                    price.mrp
                    >
                    price.price
                ):

                    price_html += (
                        "<span class='mrp'>"
                        "₹"
                        +
                        f"{float(price.mrp):,.0f}"
                        +
                        "</span>"
                    )

                if price.discount_percent:

                    price_html += (
                        "<span class='discount'>"
                        +
                        f"{price.discount_percent:.0f}% OFF"
                        +
                        "</span>"
                    )

            else:

                price_html = (
                    "Price unavailable"
                )

            if product.image_url:

                image = f"""

<img
class="card-image"
src="{product.image_url}"
alt=""
loading="lazy"
onerror="this.style.display='none'"
>

"""

            else:

                image = """

<div class="no-image">
NO IMAGE
</div>

"""

            rating = ""

            if product.rating:

                rating = (
                    "★ "
                    +
                    f"{product.rating:.1f}"
                )

            html += f"""

<article class="card">

{image}

<div class="card-body">

<div class="card-meta">

{
product.category.name
if product.category
else
"Product"
}

"""

            if product.brand:

                html += (
                    " · "
                    +
                    product.brand.name
                )

            html += f"""

</div>

<div class="card-title">
{product.name}
</div>

<div class="price">
{price_html}
</div>

<div class="card-meta">
{rating}
"""

            if product.rating_count:

                html += (
                    " · "
                    +
                    str(
                        product.rating_count
                    )
                    +
                    " ratings"
                )

            html += """

</div>

<div class="actions">

<a
class="action"
href="/product/"""
            html += str(
                product.id
            )
            html += """
">
Details
</a>

<a
class="action"
href="/compare?a="""
            html += str(
                product.id
            )
            html += """
">
Compare
</a>

</div>

</div>

</article>

"""

        html += """

</div>

"""

        if pagination.pages > 1:

            html += """

<div class="toolbar"
style="margin-top:30px"
>

"""

            if pagination.has_prev:

                html += f"""

<a
class="secondary"
href="?q={q}&category={category_slug}&page={pagination.prev_num}"
>
← Previous
</a>

"""

            html += f"""

<span class="pill">
Page {pagination.page}
of {pagination.pages}
</span>

"""

            if pagination.has_next:

                html += f"""

<a
class="secondary"
href="?q={q}&category={category_slug}&page={pagination.next_num}"
>
Next →
</a>

"""

            html += """

</div>

"""

    html += """

</section>

"""

    return render_template_string(
        PAGE,
        title="Products",
        content=render_template_string(
            html,
            q=q
        )
    )


# ============================================================
# PRODUCT DETAIL
# ============================================================

@app.get(
    "/product/<int:product_id>"
)
def product_detail(
    product_id
):

    product = db.session.get(
        Product,
        product_id
    )

    if product is None:

        return (
            "Product not found",
            404
        )

    price = latest_price(
        product
    )

    if (
        price
        and
        price.price is not None
    ):

        price_html = (
            "₹"
            +
            f"{float(price.price):,.0f}"
        )

    else:

        price_html = (
            "Price unavailable"
        )

    if product.image_url:

        image_html = f"""

<img
class="detail-image"
src="{product.image_url}"
alt=""
>

"""

    else:

        image_html = """

<div
class="no-image"
style="height:550px"
>
NO IMAGE
</div>

"""

    html = f"""

<section class="container">

<div class="detail">

<div>

{image_html}

</div>


<div class="detail-content">

<div class="eyebrow">
{
product.category.name
if product.category
else
"PRODUCT"
}
</div>

<h1 class="detail-title">
{product.name}
</h1>

"""

    if product.brand:

        html += f"""

<p class="muted">
Brand:
<strong>
{product.brand.name}
</strong>
</p>

"""

    if product.rating:

        html += f"""

<span class="rating">
★ {product.rating:.1f}
"""

        if product.rating_count:

            html += (
                " · "
                +
                str(
                    product.rating_count
                )
            )

        html += """

</span>

"""

    html += f"""

<div class="big-price">
{price_html}
</div>

"""

    if (
        price
        and
        price.mrp
        and
        price.mrp
        >
        price.price
    ):

        html += f"""

<p class="muted">
MRP:
<s>
₹{float(price.mrp):,.0f}
</s>

"""

        if price.discount_percent:

            html += (
                f" · "
                f"{price.discount_percent:.0f}% off"
            )

        html += """

</p>

"""

    html += f"""

<p class="muted">
Availability:
{
product.availability
or
"Unknown"
}
</p>

"""

    if product.description:

        html += f"""

<p
class="muted"
style="line-height:1.7"
>
{product.description}
</p>

"""

    html += """

<div class="actions">

<a
class="primary"
href="/compare?a="""

    html += str(
        product.id
    )

    html += """

">
COMPARE
</a>

"""

    if product.product_url:

        html += f"""

<a
class="secondary"
href="{product.product_url}"
target="_blank"
rel="noopener noreferrer"
>
OPEN FLIPKART ↗
</a>

"""

    html += """

</div>

</div>

</div>


<section style="margin-top:70px">

<div class="eyebrow">
SPECS
</div>

<h2>
Key specifications
</h2>

"""

    if product.specifications:

        for spec in product.specifications:

            html += f"""

<div class="spec">

<strong>
{spec.name}
</strong>

<div class="muted"
style="margin-top:5px"
>
{spec.value}
</div>

</div>

"""

    else:

        html += """

<div class="empty">

No specifications stored yet.

</div>

"""

    html += """

</section>


<section style="margin-top:70px">

<div class="eyebrow">
PRICE DATA
</div>

<h2>
Recent price history
</h2>

<div class="compare-table">

<div class="compare-row compare-head">

<div>
Date
</div>

<div>
Price
</div>

<div>
MRP
</div>

</div>

"""

    history = (
        PriceHistory.query
        .filter_by(
            product_id=product.id
        )
        .order_by(
            PriceHistory.checked_at.desc()
        )
        .limit(20)
        .all()
    )

    for item in history:

        p = (
            "₹"
            +
            f"{float(item.price):,.0f}"
            if item.price is not None
            else
            "Unavailable"
        )

        m = (
            "₹"
            +
            f"{float(item.mrp):,.0f}"
            if item.mrp is not None
            else
            "Unavailable"
        )

        date = (
            item.checked_at.strftime(
                "%Y-%m-%d %H:%M"
            )
            if item.checked_at
            else
            "-"
        )

        html += f"""

<div class="compare-row">

<div>
{date}
</div>

<div>
{p}
</div>

<div>
{m}
</div>

</div>

"""

    html += """

</div>

</section>

</section>

"""

    return render_template_string(
        PAGE,
        title=product.name,
        content=html
    )


# ============================================================
# COMPARE
# ============================================================

def comparison_verdict(product_a, product_b, price_a, price_b):
    def score(product, price):
        rating = min(max(float(product.rating or 0), 0), 5) / 5 * 60
        reviews = min(20, (max(int(product.rating_count or 0), 0) ** 0.5) / 10)
        value = min(20, max(float(product.rating or 0), 0) * 2) if price and price.price is not None else 0
        return round(rating + reviews + value, 1)
    sa, sb = score(product_a, price_a), score(product_b, price_b)
    winner = product_a if sa > sb else product_b if sb > sa else None
    return {"title": f"🏆 Overall Winner: {winner.name}" if winner else "🤝 Too Close To Call",
            "info": f"{winner.name} has the stronger score from the available rating, review-count and value data." if winner else "Both products received the same score. The lucky draw below can settle it just for fun.",
            "score_a": sa, "score_b": sb, "winner_id": winner.id if winner else None}


@app.get("/compare")
def compare():

    id_a = request.args.get(
        "a",
        type=int
    )

    id_b = request.args.get(
        "b",
        type=int
    )

    product_a = (
        db.session.get(
            Product,
            id_a
        )
        if id_a
        else None
    )

    product_b = (
        db.session.get(
            Product,
            id_b
        )
        if id_b
        else None
    )

    html = """

<section class="container">

<div class="eyebrow">
SIDE-BY-SIDE
</div>

<h2>
Compare products
</h2>

<p class="muted">
Choose two products already stored
in your database.
</p>

<form
class="compare-picker"
method="get"
>

<div class="picker">

<label>
PRODUCT A
</label>

<input
id="searchA"
value="
"""

    if product_a:

        html += product_a.name

    html += """
"
placeholder="Search product A..."
autocomplete="off"
>

<input
id="idA"
name="a"
type="hidden"
value="
"""

    if product_a:

        html += str(
            product_a.id
        )

    html += """
"
>

<div
id="resultsA"
class="suggestions"
>
</div>

</div>


<div class="vs">
VS
</div>


<div class="picker">

<label>
PRODUCT B
</label>

<input
id="searchB"
value="
"""

    if product_b:

        html += product_b.name

    html += """
"
placeholder="Search product B..."
autocomplete="off"
>

<input
id="idB"
name="b"
type="hidden"
value="
"""

    if product_b:

        html += str(
            product_b.id
        )

    html += """
"
>

<div
id="resultsB"
class="suggestions"
>
</div>

</div>


<button
class="primary"
>
COMPARE
</button>

</form>

"""

    if product_a and product_b:

        price_a = latest_price(
            product_a
        )

        price_b = latest_price(
            product_b
        )

        def price_text(
            price
        ):

            if (
                price
                and
                price.price is not None
            ):

                return (
                    "₹"
                    +
                    f"{float(price.price):,.0f}"
                )

            return "Unavailable"

        html += f"""

<div class="compare-table">

<div class="compare-row compare-head">

<div>
ATTRIBUTE
</div>

<div>
{product_a.name}
</div>

<div>
{product_b.name}
</div>

</div>


<div class="compare-row">

<div>
Brand
</div>

<div>
{
product_a.brand.name
if product_a.brand
else
"Unknown"
}
</div>

<div>
{
product_b.brand.name
if product_b.brand
else
"Unknown"
}
</div>

</div>


<div class="compare-row">

<div>
Price
</div>

<div>
{price_text(price_a)}
</div>

<div>
{price_text(price_b)}
</div>

</div>


<div class="compare-row">

<div>
Rating
</div>

<div>
{
product_a.rating
if product_a.rating is not None
else
"Unavailable"
}
</div>

<div>
{
product_b.rating
if product_b.rating is not None
else
"Unavailable"
}
</div>

</div>


<div class="compare-row">

<div>
Ratings count
</div>

<div>
{
product_a.rating_count
if product_a.rating_count is not None
else
"Unavailable"
}
</div>

<div>
{
product_b.rating_count
if product_b.rating_count is not None
else
"Unavailable"
}
</div>

</div>


<div class="compare-row">

<div>
Availability
</div>

<div>
{
product_a.availability
or
"Unknown"
}
</div>

<div>
{
product_b.availability
or
"Unknown"
}
</div>

</div>

"""

        specs_a = {
            spec.name:
            spec.value
            for spec in
            product_a.specifications
        }

        specs_b = {
            spec.name:
            spec.value
            for spec in
            product_b.specifications
        }

        all_specs = list(
            dict.fromkeys(
                list(specs_a.keys())
                +
                list(specs_b.keys())
            )
        )

        for name in all_specs:

            html += f"""

<div class="compare-row">

<div>
{name}
</div>

<div>
{specs_a.get(
    name,
    "Unavailable"
)}
</div>

<div>
{specs_b.get(
    name,
    "Unavailable"
)}
</div>

</div>

"""

        html += """

</div>

"""

        verdict = comparison_verdict(product_a, product_b, price_a, price_b)
        winner_class_a = "verdict-winner" if verdict["winner_id"] == product_a.id else ""
        winner_class_b = "verdict-winner" if verdict["winner_id"] == product_b.id else ""
        html += f'''
<div class="verdict-card">
<div class="eyebrow">FINAL VERDICT</div>
<div class="verdict-title">{verdict["title"]}</div>
<p class="muted">{verdict["info"]}</p>
<div class="verdict-grid">
<div class="verdict-box {winner_class_a}"><strong>{product_a.name}</strong><div class="big-price">{verdict["score_a"]}/100</div></div>
<div class="verdict-box {winner_class_b}"><strong>{product_b.name}</strong><div class="big-price">{verdict["score_b"]}/100</div></div>
</div>
</div>
<div class="lucky-card">
<div class="eyebrow">STILL CAN'T DECIDE?</div>
<h2>Let the lucky draw decide. 🎡</h2>
<p class="muted">The final verdict is shown first. Now let a 50/50 wheel choose between these same two products.</p>
<div class="wheel-wrap"><div class="wheel-pointer"></div><div id="compareWheel" class="wheel"></div></div>
<div style="text-align:center"><button class="primary" type="button" id="spinCompareWheel">SPIN THE LUCKY WHEEL</button></div>
<div id="compareLuckyResult" class="lucky-result" style="margin-top:18px">Ready. 50/50. No pressure. 😂</div>
</div>
<script>
(function(){{
const b=document.getElementById("spinCompareWheel");
const w=document.getElementById("compareWheel");
const r=document.getElementById("compareLuckyResult");
const a={json.dumps(product_a.name)};
const c={json.dumps(product_b.name)};
let rotation=0;
b.addEventListener("click",function(){{
b.disabled=true;
r.textContent="Spinning... 🎡";
const pickA=Math.random()<0.5;
rotation += (5+Math.floor(Math.random()*3))*360 + (pickA?25:205);
w.style.transform="rotate("+rotation+"deg)";
setTimeout(function(){{
r.textContent="🎉 THE LUCKY DRAW CHOOSES: "+(pickA?a:c)+" — Fate has spoken. 😂";
b.disabled=false;
}},3100);
}});
}})();
</script>
'''
    html += """

</section>


<script>

function escapeHtml(value) {

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");

}


function setupPicker(
    searchId,
    hiddenId,
    resultsId
) {

    const search =
        document.getElementById(
            searchId
        );

    const hidden =
        document.getElementById(
            hiddenId
        );

    const results =
        document.getElementById(
            resultsId
        );

    if (!search) {
        return;
    }

    let timer = null;

    search.addEventListener(
        "input",
        function() {

            clearTimeout(timer);

            hidden.value = "";

            const q =
                search.value.trim();

            if (!q) {

                results.innerHTML = "";

                return;
            }

            timer = setTimeout(
                async function() {

                    try {

                        const response =
                            await fetch(
                                "/api/search?q="
                                +
                                encodeURIComponent(
                                    q
                                )
                            );

                        const items =
                            await response.json();

                        results.innerHTML = "";

                        items.forEach(
                            function(item) {

                                const button =
                                    document.createElement(
                                        "button"
                                    );

                                button.type =
                                    "button";

                                button.className =
                                    "suggestion";

                                button.innerHTML =
                                    "<strong>"
                                    +
                                    escapeHtml(
                                        item.name
                                    )
                                    +
                                    "</strong>"
                                    +
                                    "<small>"
                                    +
                                    escapeHtml(
                                        item.category
                                    )
                                    +
                                    " · "
                                    +
                                    escapeHtml(
                                        item.brand
                                    )
                                    +
                                    "</small>";

                                button.onclick =
                                    function() {

                                        hidden.value =
                                            item.id;

                                        search.value =
                                            item.name;

                                        results.innerHTML =
                                            "";

                                    };

                                results.appendChild(
                                    button
                                );

                            }
                        );

                    }
                    catch (error) {

                        results.innerHTML =
                            "<div class='suggestion'>"
                            +
                            "Search failed"
                            +
                            "</div>";

                    }

                },
                250
            );

        }
    );

}


setupPicker(
    "searchA",
    "idA",
    "resultsA"
);


setupPicker(
    "searchB",
    "idB",
    "resultsB"
);

</script>

"""

    return render_template_string(
        PAGE,
        title="Compare",
        content=html
    )


# ============================================================
# DATABASE / ADMIN PAGE
# ============================================================

@app.get("/admin")
def admin():

    total = Product.query.count()

    categories = []

    for slug, config in CATEGORY_CONFIG.items():

        category = Category.query.filter_by(
            slug=slug
        ).first()

        count = (
            Product.query.filter_by(
                category_id=category.id
            ).count()
            if category
            else
            0
        )

        categories.append(
            {
                "slug": slug,
                "name": config["name"],
                "count": count,
                "target":
                    PRODUCT_TARGET_PER_CATEGORY
            }
        )

    html = """

<section class="container">

<div class="eyebrow">
DATABASE CONTROL CENTER
</div>

<h2>
Your database
</h2>

<p class="muted">

This page controls the real ReefAPI →
SQLite import. Products are not fake
or hard-coded.

</p>


<div class="stats">

<div class="stat">

<div class="stat-number">
"""

    html += str(total)

    html += """

</div>

<div class="stat-label">
Products
</div>

</div>


<div class="stat">

<div class="stat-number">
"""

    html += str(
        len(CATEGORY_CONFIG)
    )

    html += """

</div>

<div class="stat-label">
Categories
</div>

</div>


<div class="stat">

<div class="stat-number">
"""

    html += str(
        PRODUCT_TARGET_PER_CATEGORY
    )

    html += """

+</div>

<div class="stat-label">
Target per category
</div>

</div>


<div class="stat">

<div class="stat-number">
"""

    html += (
        "CONNECTED"
        if REEF_API_KEY
        else
        "MISSING"
    )

    html += """

</div>

<div class="stat-label">
ReefAPI
</div>

</div>

</div>


<div class="sync-panel">

<div class="eyebrow">
FULL IMPORT
</div>

<h3>
Build the complete database
</h3>

<p class="muted">

This will search multiple ReefAPI queries
until each category reaches the configured
target. Existing products are deduplicated.

</p>

<button
class="primary"
id="syncAll"
onclick="syncAll()"
>
SYNC 100 EACH CATEGORY
</button>

<div
id="syncStatus"
class="muted"
style="margin-top:18px"
>
Ready.
</div>

</div>


<div class="sync-grid">

"""

    for category in categories:

        status_class = (
            "ok"
            if category["count"]
            >=
            category["target"]
            else
            ""
        )

        html += f"""

<div class="sync-row">

<div>

<strong>
{category["name"]}
</strong>

<div class="muted">
{category["count"]}
/
{category["target"]}
products
</div>

</div>

<div class="{status_class}">

{
"COMPLETE"
if
category["count"]
>=
category["target"]
else
"NEEDS DATA"
}

</div>

</div>

"""

    html += """

</div>


<div
class="sync-panel"
style="margin-top:25px"
>

<div class="eyebrow">
DATABASE LOCATION
</div>

<h3>
comparex.db
</h3>

<p class="muted">
The SQLite database is automatically created
beside your app.py file.
</p>

</div>

</section>


<script>

async function syncAll() {

    const button =
        document.getElementById(
            "syncAll"
        );

    const status =
        document.getElementById(
            "syncStatus"
        );

    button.disabled = true;

    button.textContent =
        "SYNCING...";

    status.textContent =
        "Contacting ReefAPI and building the database...";

    try {

        const response =
            await fetch(
                "/api/admin/sync-all",
                {
                    method: "POST",
                    headers: {
                        "Content-Type":
                            "application/json"
                    },
                    body: JSON.stringify({
                        target: 100
                    })
                }
            );

        const data =
            await response.json();

        if (!response.ok) {

            throw new Error(
                data.error
                ||
                "Sync failed"
            );

        }

        let complete = 0;
        let totalAdded = 0;

        Object.values(data).forEach(
            function(item) {

                if (item.complete) {
                    complete++;
                }

                totalAdded +=
                    item.added || 0;

            }
        );

        status.innerHTML =
            "<span class='ok'>"
            +
            "Sync finished. "
            +
            complete
            +
            "/7 categories reached target. "
            +
            totalAdded
            +
            " new products added."
            +
            "</span>";

        button.textContent =
            "SYNC COMPLETE";

        setTimeout(
            function() {
                location.reload();
            },
            1800
        );

    }
    catch (error) {

        status.innerHTML =
            "<span class='bad'>"
            +
            escapeHtml(
                error.message
            )
            +
            "</span>";

        button.disabled = false;

        button.textContent =
            "TRY AGAIN";

    }

}


function escapeHtml(value) {

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");

}

</script>

"""

    return render_template_string(
        PAGE,
        title="Database",
        content=html
    )


# ============================================================
# DATABASE SEARCH API
# ============================================================

@app.get("/api/search")
def api_search():

    q = request.args.get(
        "q",
        ""
    ).strip()

    if not q:

        return jsonify([])

    like = f"%{q}%"

    items = (
        Product.query
        .filter(
            or_(
                Product.name.ilike(
                    like
                ),
                Product.model.ilike(
                    like
                ),
                Product.external_id.ilike(
                    like
                )
            )
        )
        .order_by(
            Product.updated_at.desc()
        )
        .limit(20)
        .all()
    )

    return jsonify(
        [
            {
                "id": product.id,
                "name": product.name,
                "brand":
                    product.brand.name
                    if product.brand
                    else "Unknown",
                "category":
                    product.category.name
                    if product.category
                    else "Unknown"
            }
            for product in items
        ]
    )


# ============================================================
# PRODUCT API
# ============================================================

@app.get(
    "/api/product/<int:product_id>"
)
def api_product(
    product_id
):

    product = db.session.get(
        Product,
        product_id
    )

    if product is None:

        return jsonify(
            {
                "error":
                    "Product not found"
            }
        ), 404

    return jsonify(
        product_json(
            product
        )
    )


# ============================================================
# DATABASE STATS API
# ============================================================

@app.get("/api/stats")
def api_stats():

    categories = {}

    for slug, config in CATEGORY_CONFIG.items():

        category = Category.query.filter_by(
            slug=slug
        ).first()

        count = (
            Product.query.filter_by(
                category_id=category.id
            ).count()
            if category
            else
            0
        )

        categories[slug] = {
            "name":
                config["name"],
            "count":
                count,
            "target":
                PRODUCT_TARGET_PER_CATEGORY,
            "complete":
                count
                >=
                PRODUCT_TARGET_PER_CATEGORY
        }

    return jsonify(
        {
            "database":
                str(DATABASE_FILE),
            "total_products":
                Product.query.count(),
            "categories":
                categories,
            "reefapi_configured":
                bool(REEF_API_KEY)
        }
    )


# ============================================================
# TEST REEFAPI
# ============================================================

@app.post(
    "/api/admin/test-reefapi"
)
def api_test_reefapi():

    if not REEF_API_KEY:

        return jsonify(
            {
                "ok": False,
                "error":
                    "REEF_API_KEY is missing."
            }
        ), 400

    body = (
        request.get_json(
            silent=True
        )
        or {}
    )

    query = (
        body.get(
            "query"
        )
        or
        "smartphone"
    )

    try:

        response = reef_search(
            query,
            1
        )

        rows = result_rows(
            response
        )

        return jsonify(
            {
                "ok": True,
                "query": query,
                "records":
                    len(rows),
                "response":
                    response
            }
        )

    except Exception as exc:

        return jsonify(
            {
                "ok": False,
                "error":
                    str(exc)
            }
        ), 500


# ============================================================
# SYNC SINGLE CATEGORY API
# ============================================================

@app.post(
    "/api/admin/sync/<category_slug>"
)
def api_sync_category(
    category_slug
):

    body = (
        request.get_json(
            silent=True
        )
        or
        {}
    )

    target = body.get(
        "target",
        PRODUCT_TARGET_PER_CATEGORY
    )

    try:

        result = sync_category(
            category_slug,
            target
        )

        return jsonify(
            {
                "ok": True,
                **result
            }
        )

    except Exception as exc:

        return jsonify(
            {
                "ok": False,
                "error":
                    str(exc)
            }
        ), 500


# ============================================================
# SYNC EVERYTHING
# ============================================================

@app.post(
    "/api/admin/sync-all"
)
def api_sync_all():

    body = (
        request.get_json(
            silent=True
        )
        or
        {}
    )

    target = body.get(
        "target",
        PRODUCT_TARGET_PER_CATEGORY
    )

    try:

        results = sync_all_categories(
            target
        )

        return jsonify(
            results
        )

    except Exception as exc:

        return jsonify(
            {
                "ok": False,
                "error":
                    str(exc)
            }
        ), 500


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health():

    return jsonify(
        {
            "status": "ok",
            "database":
                DATABASE_FILE.exists(),
            "reefapi":
                bool(REEF_API_KEY),
            "products":
                Product.query.count()
        }
    )


# ============================================================
# ERROR HANDLING
# ============================================================

@app.errorhandler(404)
def not_found(error):

    return render_template_string(
        PAGE,
        title="Not Found",
        content="""

<section class="container">

<div class="empty">

<h2>
404
</h2>

<p>
The page you're looking for doesn't exist.
</p>

<a
class="primary"
href="/"
>
GO HOME
</a>

</div>

</section>

"""
    ), 404


# ============================================================
# DATABASE STARTUP
# ============================================================

with app.app_context():

    initialize_database()


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    port = int(
        os.getenv(
            "PORT",
            "5000"
        )
    )

    print()
    print("=" * 70)
    print("COMPAREX")
    print("=" * 70)
    print(
        "Database:",
        DATABASE_FILE
    )
    print(
        "Database exists:",
        DATABASE_FILE.exists()
    )
    with app.app_context():
        total_products = Product.query.count()

    print(
        "Products:",
        total_products
    )
    print(
        "ReefAPI:",
        "CONNECTED"
        if REEF_API_KEY
        else
        "MISSING KEY"
    )
    print(
        "Target/category:",
        PRODUCT_TARGET_PER_CATEGORY
    )
    print(
        "Target total:",
        PRODUCT_TARGET_PER_CATEGORY
        *
        len(CATEGORY_CONFIG)
    )
    print(
        "URL:",
        f"http://127.0.0.1:{port}"
    )
    print("=" * 70)
    print()

    app.run(
        host="127.0.0.1",
        port=port,
        debug=True
    )
