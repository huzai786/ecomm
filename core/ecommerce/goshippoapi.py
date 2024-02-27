import shippo

shippo.config.api_key = "shippo_test_ae96b56136cb33f7e0a95bb37b73ade07d5c37e4"

def validate_address(name, email, street1, city, state, zip, country, street2=""):
    addr = shippo.Address.create(
        name=name,
        street1 = street1,
        street2 = street2,
        city=city,
        state=state,
        zip=zip,
        country=country,
        email=email,
        validate=True
    )
    if addr.validation_results.is_valid and addr.is_complete:
        return addr.object_id
    else:
        raise Exception('invalid address')

def get_shipping_rates(address_from, address_to, parcel):
    shipment = shippo.Shipment.create(
        address_from = address_from,
        address_to = address_to,
        parcels = [parcel],
        asynchronous = False
    )

    # Extract relevant information from the rates list
    rates_info = [extract_rate_info(rate) for rate in shipment.rates[:5]]
    return rates_info

def extract_rate_info(rate):
    return {
            'object_id': rate.get('object_id', ''),
            'amount_local': rate.get('amount_local', ''),
            'currency_local': rate.get('currency_local', ''),
            'provider': rate.get('provider', ''),
            'estimated_days': rate.get('estimated_days', ''),
            'duration_terms': rate.get('duration_terms', ''),
    }

def amount_from_rateid(rate_id):
    amount_local = float(shippo.Rate.retrieve(rate_id).get("amount_local"))
    return amount_local


def purchase_shipment_rate(rate_id):
    transaction = shippo.Transaction.create( 
    rate=rate_id, 
    label_file_type="PDF", 
    asynchronous=False )
    if transaction.status == "SUCCESS":
        return (transaction.tracking_url_provider, transaction.label_url)

    else:
        raise Exception("Unable to create shipment please contact Us!")

