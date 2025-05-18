import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions
from textblob import TextBlob
import csv
import io

class ParseCSV(beam.DoFn):
    def process(self, element):
        reader = csv.DictReader(io.StringIO(element), fieldnames=['timestamp', 'text'])
        next(reader)  # Skip header
        for row in reader:
            yield row

class AnalyzeEmotion(beam.DoFn):
    def process(self, row):
        text = row['text']
        timestamp = row['timestamp']
        cities = ['北京', '上海', '广州', '深圳']
        city = next((c for c in cities if c in text), '未知')
        sentiment = TextBlob(text).sentiment.polarity
        yield {
            'timestamp': timestamp,
            'city': city,
            'sentiment': sentiment
        }

def run():
    options = PipelineOptions(
        runner='DataflowRunner',
        project='beam-emotion-map',
        region='us-central1',
        temp_location='gs://beam-emotion-data/tmp',
        save_main_session=True
    )

    with beam.Pipeline(options=options) as p:
        (
            p
            | 'ReadFile' >> beam.io.ReadFromText('./comments.csv', skip_header_lines=1)
            | 'ParseCSV' >> beam.ParDo(ParseCSV())
            | 'AnalyzeEmotion' >> beam.ParDo(AnalyzeEmotion())
            | 'WriteToBigQuery' >> beam.io.WriteToBigQuery(
                'beam-emotion-map:analytics.city_emotion',
                schema='timestamp:TIMESTAMP,city:STRING,sentiment:FLOAT',
                write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
                create_disposition=beam.io.BigQueryDisposition.CREATE_IF_NEEDED
            )
        )

if __name__ == '__main__':
    run()
