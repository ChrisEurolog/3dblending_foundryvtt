import os

def check_file_exists(filepath):
    if os.path.exists(filepath):
        print(f"✅ File {filepath} exists.")
        return True
    else:
        print(f"❌ File {filepath} is missing.")
        return False

def check_agents_md():
    with open("AGENTS.md", "r") as f:
        content = f.read()
        if "SHA256 hashes" in content and "lock file" in content:
            print("✅ AGENTS.md contains dependency lock instructions.")
            return True
        else:
            print("❌ AGENTS.md is missing dependency lock instructions.")
            return False

def main():
    all_passed = True
    all_passed &= check_file_exists("requirements.in")
    all_passed &= check_file_exists("requirements.txt")
    all_passed &= check_agents_md()

    if all_passed:
        print("\n🎉 All verifications passed!")
    else:
        print("\n⚠️ Some verifications failed.")
        exit(1)

if __name__ == "__main__":
    main()
