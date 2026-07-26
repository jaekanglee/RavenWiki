import os
import shutil

# Files to update contents
replacements = {
    'com.myapplication.MyApplication': 'com.ppizil.raven',
    'com.myapplication.common': 'com.ppizil.raven.common',
    'com.myapplication': 'com.ppizil.raven',
}

def replace_in_file(filepath):
    if not os.path.exists(filepath):
        return
    with open(filepath, 'r') as f:
        content = f.read()
        
    original = content
    for old, new in replacements.items():
        content = content.replace(old, new)
        
    if original != content:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"Updated {filepath}")

files_to_update = [
    'mobile/androidApp/build.gradle.kts',
    'mobile/shared/build.gradle.kts',
    'mobile/iosApp/Configuration/Config.xcconfig',
    'mobile/androidApp/src/androidMain/AndroidManifest.xml'
]

for f in files_to_update:
    replace_in_file(f)

# Find all kt files and update their contents
for root, dirs, files in os.walk('mobile'):
    if 'build' in root:
        continue
    for file in files:
        if file.endswith('.kt'):
            replace_in_file(os.path.join(root, file))

# Move directories
def move_dir(old_path, new_path):
    if os.path.exists(old_path):
        os.makedirs(os.path.dirname(new_path), exist_ok=True)
        shutil.move(old_path, new_path)
        print(f"Moved {old_path} to {new_path}")

# Android App source
move_dir(
    'mobile/androidApp/src/androidMain/kotlin/com/myapplication',
    'mobile/androidApp/src/androidMain/kotlin/com/ppizil/raven'
)

# Shared commonMain source
move_dir(
    'mobile/shared/src/commonMain/kotlin/com/myapplication/common',
    'mobile/shared/src/commonMain/kotlin/com/ppizil/raven/common'
)

# Shared androidUnitTest source
move_dir(
    'mobile/shared/src/androidUnitTest/kotlin/com/myapplication/common',
    'mobile/shared/src/androidUnitTest/kotlin/com/ppizil/raven/common'
)

# SQLDelight
move_dir(
    'mobile/shared/src/commonMain/sqldelight/com/myapplication/common',
    'mobile/shared/src/commonMain/sqldelight/com/ppizil/raven/common'
)

print("Done renaming package!")
