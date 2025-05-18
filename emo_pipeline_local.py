import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions
from textblob import TextBlob
import csv
import io

class ParseCSV(beam.DoFn):
    def process(self, element):
        reader = csv.DictReader(io.StringIO(element), fieldnames=['timestamp', 'text'])
        yield from reader

class AnalyzeEmotion(beam.DoFn):
    def process(self, row):
        text = row['text']
        timestamp = row['timestamp']
        cities = ['Beijing', 'Shanghai', 'Guangzhou', 'Shenzhen']
        city = next((c for c in cities if c in text), 'Unknown')
        sentiment = TextBlob(text).sentiment.polarity
        subjectivity = TextBlob(text).sentiment.subjectivity
        return [{
            'timestamp': timestamp,
            'city': city,
            'sentiment': sentiment,
            'subjectivity': subjectivity
        }]

def to_csv_line(element):
    return f"{element['timestamp']},{element['city']},{element['sentiment']},{element['subjectivity']}"

def run():
    options = PipelineOptions(
        runner='DirectRunner',
        save_main_session=True,
    )

    with beam.Pipeline(options=options) as p:
        (
            p
            | 'ReadCSV' >> beam.io.ReadFromText('comments.csv', skip_header_lines=1)
            | 'ParseCSV' >> beam.ParDo(ParseCSV())
            | 'AnalyzeEmotion' >> beam.ParDo(AnalyzeEmotion())
            | 'FormatToCSV' >> beam.Map(to_csv_line)
            | 'WriteCSV' >> beam.io.WriteToText('emotion_output/emotions', file_name_suffix='.csv', shard_name_template='')  # output single CSV file
        )

if __name__ == '__main__':
    run()
