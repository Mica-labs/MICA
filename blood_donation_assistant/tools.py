donors = {
    "Klaus": {
        "address": "Goleta, CA",
        # "gender": "M",
        # "age": 21,
    },
    "Kim": {
        "address": "London, England",
        # "gender": "M",
        # "age": 21,
    }
}

def get_donor_info(name):
    if name in donors:
        return [{"arg": "address", "value": donors[name]["address"]}]
        # return [{
        #     "name": name,
        #     # "gender": donors[name]["gender"],
        #     "address": donors[name]["address"]
        #     # "age": donors[name]["age"],
        # }]
    else:
        return f"No donor found with the name '{name}'."

#print(get_donor_info("Klaus"))

