from markitdown import MarkItDown
import os

def convert_html_to_md():
    # Initialize MarkItDown
    md = MarkItDown()
    
    # Convert HTML to markdown
    result = md.convert("123.html")
    
    # Generate output filename (same name but .md extension)
    output_filename = os.path.splitext("123.html")[0] + ".md"
    
    # Save the content to markdown file
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(result.text_content)
    
    print(f"Conversion complete. Saved to {output_filename}")

if __name__ == "__main__":
    convert_html_to_md()