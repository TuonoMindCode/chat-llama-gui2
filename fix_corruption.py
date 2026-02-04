import json

with open('qt_tabs/qt_base_chat_tab.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the problematic section
# It starts with self.display_message(message, is_user=True, timestamp=timestamp)
# Then has embedded JSON
# And we need to find where "Clear input field" comment appears

bad_start = content.find('self.display_message(message, is_user=True, timestamp=timestamp)\n  "system_prompt":')
if bad_start != -1:
    # Find the end - it's right before the next clean Python line
    bad_end = content.find('        # Clear input field and reset to minimal height', bad_start)
    if bad_end != -1:
        # Remove everything from the newline after display_message to right before the comment
        before = content[:bad_start + len('self.display_message(message, is_user=True, timestamp=timestamp)')]
        after = content[bad_end:]
        content = before + '\n        \n        ' + after
        
with open('qt_tabs/qt_base_chat_tab.py', 'w', encoding='utf-8') as f:
    f.write(content)
    
print("File cleaned")
