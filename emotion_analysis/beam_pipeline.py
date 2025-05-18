import apache_beam as beam
from apache_beam.io.kafka import ReadFromKafka
from apache_beam.io import WriteToText
from apache_beam.options.pipeline_options import PipelineOptions
from apache_beam.transforms.window import FixedWindows
import json
from datetime import datetime
import requests
import os

class ParseJson(beam.DoFn):
    def process(self, element):
        try:
            print(f"[ParseJson] DECODING...")
            message_value = element[1].decode('utf-8') if isinstance(element[1], bytes) else element[1]
            print(f"[ParseJson] DECODED: {message_value}")
            comment = json.loads(message_value)
            yield comment
        except Exception as e:
            print(f"Failed to parse message: {e}")

class AnalyzeSentiment(beam.DoFn):
    def __init__(self):
        self.hf_api_token = os.getenv("HF_API_TOKEN")
        self.hf_api_url = "https://api-inference.huggingface.co/models/distilbert-base-uncased-finetuned-sst-2-english"
        self.headers = {
            "Authorization": f"Bearer {self.hf_api_token}"
        }

    def process(self, comment):
        try:
            text = comment.get('text', '')
            location = comment.get('location', 'Unknown')
            if not text:
                return

            payload = {"inputs": text}
            response = requests.post(self.hf_api_url, headers=self.headers, json=payload, timeout=10)

            if response.status_code == 200:
                result = response.json()
                pred = result[0]
                label = pred.get('label', 'NEUTRAL')
                score = pred.get('score', 0.0)

                sentiment_value = {
                    'POSITIVE': 1.0,
                    'NEGATIVE': -1.0,
                    'NEUTRAL': 0.0
                }.get(label.upper(), 0.0)

                yield {
                    'location': location,
                    'sentiment': sentiment_value,
                    'text': text,
                    'confidence': score,
                    'label': label,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                print(f"HuggingFace API error {response.status_code}: {response.text}")

        except Exception as e:
            print(f"HuggingFace API call failed: {e}")

class ToCSVLine(beam.DoFn):
    def process(self, element):
        try:
            clean_text = element['text'].replace('"', "'").replace('\n', ' ')
            yield f'"{element["location"]}",{element["sentiment"]:.4f},"{clean_text}","{element["timestamp"]}"'
        except Exception as e:
            print(f"CSV formatting failed: {e}")

def run():
    options = PipelineOptions([
        '--runner=FlinkRunner',
        '--flink_master=flink-jobmanager:8081',
        '--flink_version=1.16',
        '--parallelism=1'
    ])

    with beam.Pipeline(options=options) as p:
        (
            p
            | 'ReadFromKafka' >> ReadFromKafka(
                consumer_config={
                    'bootstrap.servers': 'kafka:9092',
                    'auto.offset.reset': 'earliest',
                    'group.id': 'beam-debug-group'
                },
                topics=['comments']
            )

            | 'Window' >> beam.WindowInto(FixedWindows(5))
            | 'ParseJson' >> beam.ParDo(ParseJson()).with_output_types(dict)
            | 'AnalyzeSentiment' >> beam.ParDo(AnalyzeSentiment())
            | 'FormatCSV' >> beam.ParDo(ToCSVLine())
            | 'WriteCSVFile' >> WriteToText(
                file_path_prefix='output/emotion_analysis/sentiment',
                file_name_suffix='.csv',
                num_shards=1,
                shard_name_template=''
            )
        )

if __name__ == "__main__":
    run()