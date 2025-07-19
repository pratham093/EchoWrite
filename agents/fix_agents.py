import os
from pathlib import Path

def fix_agent_files():
    """Update all agent files with correct Gemini API usage"""
    
    agents_dir = Path("agents")
    
    # Read current files and update temperature usage
    files_to_fix = ["writer.py", "reviewer_agent.py", "editor_agent.py"]
    
    for filename in files_to_fix:
        filepath = agents_dir / filename
        if filepath.exists():
            print(f"Fixing {filename}...")
            
            # Read the file
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Replace incorrect temperature usage
            # Old pattern: response = self.model.generate_content(prompt, temperature=self.temperature)
            # New pattern: uses generation_config
            
            if "temperature=self.temperature)" in content:
                print(f"  - Found old temperature usage in {filename}")
                # This is a simplified fix - in production you'd want more robust replacement
                content = content.replace(
                    "response = self.model.generate_content(prompt, temperature=self.temperature)",
                    """generation_config = genai.GenerationConfig(
                temperature=self.temperature,
                max_output_tokens=8192,
            )
            
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
            )"""
                )
                
                # Make sure we have the right import
                if "from google.generativeai import GenerationConfig" not in content:
                    content = content.replace(
                        "import google.generativeai as genai",
                        "import google.generativeai as genai"
                    )
                
                # Write back
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"  ✓ Fixed {filename}")
            else:
                print(f"  - {filename} might already be fixed or has different structure")
    
    print("\nDone! Try running test_components.py again.")

if __name__ == "__main__":
    fix_agent_files()
