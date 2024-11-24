import os
import re
from sqlalchemy import create_engine, exc, text

class EartipReviewParser:
    def __init__(self, text_path):
        self.text_path = text_path

        # Get PostgreSQL URL from environment variable
        self.db_url = os.getenv('PG_URL')
        if not self.db_url:
            raise EnvironmentError("Environment variable 'PG_URL' not set or empty.")
        
        # Verify text file existence
        if not os.path.exists(text_path):
            raise FileNotFoundError(f"Text file not found: {text_path}")

        self.engine = create_engine(self.db_url)

    def read_text_file(self):
        """
        Reads content from text file
        """
        try:
            print(f"Reading text file from {self.text_path}")
            with open(self.text_path, 'r', encoding='utf-8') as file:
                content = file.read()
            return content
        except Exception as e:
            print(f"Error reading text file: {e}")
            raise

    def parse_reviews(self, content):
        """
        Parses eartip reviews from text content
        """
        review_pattern = r'([A-Za-z0-9\s]+?)\nBore size:\s*(.*?)\nStem length:\s*(.*?)\nFeel:\s*(.*?)\nBass:\s*([\d.]+)\nMidrange:\s*([\d.]+)\nTreble:\s*([\d.]+)\nSoundstage:\s*([\d.]+)\nVocal presence:\s*([\d.]+)'
        
        reviews = []
        matches = re.finditer(review_pattern, content)
        
        for match in matches:
            try:
                review = {
                    'product': match.group(1).strip(),
                    'bore_size': match.group(2).strip(),
                    'stem_length': match.group(3).strip(),
                    'feel': match.group(4).strip(),
                    'bass': float(match.group(5)),
                    'midrange': float(match.group(6)),
                    'treble': float(match.group(7)),
                    'soundstage': float(match.group(8)),
                    'vocal_presence': float(match.group(9))
                }
                reviews.append(review)
                print(f"Successfully parsed review for: {review['product']}")
            except (ValueError, AttributeError) as e:
                print(f"Error parsing review: {e}")
                continue

        return reviews

    def save_to_db(self, reviews):
        """
        Saves the parsed data to PostgreSQL database
        """
        insert_query = text("""
        INSERT INTO eartip_reviews (product, bore_size, stem_length, feel, bass, midrange, treble, soundstage, vocal_presence)
        VALUES (:product, :bore_size, :stem_length, :feel, :bass, :midrange, :treble, :soundstage, :vocal_presence)
        ON CONFLICT (product) DO NOTHING;
        """)

        try:
            with self.engine.connect() as conn:
                for review in reviews:
                    conn.execute(insert_query, **review)
                print(f"Data successfully saved to the database. Total reviews inserted: {len(reviews)}")
        except exc.SQLAlchemyError as e:
            print(f"Error saving to database: {e}")
            raise

    def run(self):
        """
        Main execution method
        """
        try:
            content = self.read_text_file()
            reviews = self.parse_reviews(content)
            
            if not reviews:
                print("No reviews were successfully parsed.")
                return
            
            # Save to database
            self.save_to_db(reviews)
            print(f"Processing complete. Total reviews processed: {len(reviews)}")
        except Exception as e:
            print(f"Error in main execution: {e}")
            raise

def main(text_path):
    try:
        parser = EartipReviewParser(text_path)
        parser.run()
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Parse eartip reviews from a text file and save to a PostgreSQL database')
    parser.add_argument('text_path', help='Path to the text file containing reviews')
    
    args = parser.parse_args()
    main(args.text_path)
