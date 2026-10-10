"""Fresh, unfitted transformers to put inside each estimator's sklearn Pipeline."""


def make_preprocessor(features, manifest, *, scale_numeric):
    from sklearn.compose import ColumnTransformer
    from sklearn.preprocessing import OneHotEncoder, StandardScaler

    columns = {column["name"]: column for column in manifest["columns"] if column["role"] == "input"}
    if not features or len(set(features)) != len(features) or not set(features) <= columns.keys():
        raise ValueError("Preprocessing accepts declared input columns only")
    numeric = [name for name in features if columns[name]["type"] != "category"]
    categorical = [name for name in features if columns[name]["type"] == "category"]
    transformers = []
    if numeric:
        transformers.append(("numeric", StandardScaler() if scale_numeric else "passthrough", numeric))
    if categorical:
        # Allowed levels are fixed schema metadata, not learned from holdout records.
        encoder = OneHotEncoder(categories=[columns[name]["categories"] for name in categorical],
                                drop="if_binary", handle_unknown="error", sparse_output=False)
        transformers.append(("categorical", encoder, categorical))
    return ColumnTransformer(transformers, remainder="drop")
