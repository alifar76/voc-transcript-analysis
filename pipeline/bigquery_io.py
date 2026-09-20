"""Small helper for loading the enriched VOC dataframe into BigQuery."""

from google.cloud import bigquery


def load_dataframe(df, project, dataset, table, location="US"):
    client = bigquery.Client(project=project)
    dataset_ref = bigquery.DatasetReference(project, dataset)

    try:
        client.get_dataset(dataset_ref)
    except Exception:
        ds = bigquery.Dataset(dataset_ref)
        ds.location = location
        client.create_dataset(ds)

    table_id = f"{project}.{dataset}.{table}"
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        autodetect=True,
    )
    job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
    job.result()
    return table_id, job.output_rows
