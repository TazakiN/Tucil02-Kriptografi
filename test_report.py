"""
Test Report Generator for Audio Steganography
Tests various configurations and file types with integrity checking
"""

import os
import sys
import hashlib
import random
import time
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from stegano import MultipleLSBSteganography


def calculate_md5(file_path):
    """Calculate MD5 hash of a file"""
    md5_hash = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()
    except Exception as e:
        return f"ERROR: {str(e)}"


def format_file_size(size_bytes):
    """Format file size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def get_file_size(file_path):
    """Get file size in bytes"""
    try:
        return os.path.getsize(file_path)
    except:
        return 0


class TestCase:
    def __init__(self, name, cover_file, secret_file, use_encryption, use_random, nlsb, scenario=""):
        self.name = name
        self.cover_file = cover_file
        self.secret_file = secret_file
        self.use_encryption = use_encryption
        self.use_random = use_random
        self.nlsb = nlsb
        self.scenario = scenario
        self.result = "NOT RUN"
        self.original_hash = ""
        self.extracted_hash = ""
        self.integrity = ""
        self.error_message = ""
        self.file_size = 0
        self.execution_time = 0
        self.psnr = "N/A"
        
    def to_dict(self):
        return {
            'name': self.name,
            'cover_file': os.path.basename(self.cover_file),
            'secret_file': os.path.basename(self.secret_file),
            'file_size': format_file_size(self.file_size),
            'encryption': 'YES' if self.use_encryption else 'NO',
            'random_start': 'YES' if self.use_random else 'NO',
            'nlsb': self.nlsb,
            'result': self.result,
            'integrity': self.integrity,
            'execution_time': f"{self.execution_time:.2f}s",
            'psnr': self.psnr,
            'scenario': self.scenario,
            'error': self.error_message
        }


class TestReport:
    def __init__(self):
        self.stego = MultipleLSBSteganography()
        self.test_cases = []
        self.workspace_dir = Path(__file__).parent
        self.tests_dir = self.workspace_dir / "tests"
        self.output_dir = self.workspace_dir / "test_results"
        self.extracted_dir = self.output_dir / "extracted"
        
        # Create output directories
        self.output_dir.mkdir(exist_ok=True)
        self.extracted_dir.mkdir(exist_ok=True)
        
        # Test files
        self.cover_audio = self.tests_dir / "cover.mp3"
        
    def generate_test_cases(self):
        """Generate all test cases according to specifications"""
        print("Generating test cases...")
        
        # Scenario 1: All configuration combinations with sample_secret.txt
        print("\n[Scenario 1] All configuration combinations with sample_secret.txt")
        sample_secret = self.tests_dir / "sample_secret.txt"
        
        if sample_secret.exists():
            test_configs = [
                ("Config 1: Encrypt=NO, Random=NO", False, False),
                ("Config 2: Encrypt=NO, Random=YES", False, True),
                ("Config 3: Encrypt=YES, Random=NO", True, False),
                ("Config 4: Encrypt=YES, Random=YES", True, True),
            ]
            
            for config_name, use_enc, use_rand in test_configs:
                # Test with different n-LSB values
                for nlsb in [1, 2, 3, 4]:
                    test_name = f"{config_name}, n-LSB={nlsb}"
                    self.test_cases.append(
                        TestCase(test_name, str(self.cover_audio), str(sample_secret), 
                                use_enc, use_rand, nlsb, scenario="Scenario 1")
                    )
        
        # Scenario 2: File exceeding capacity (waguri.png)
        print("[Scenario 2] Capacity overflow test with waguri.png")
        waguri_png = self.tests_dir / "waguri.png"
        if waguri_png.exists():
            # Test with minimal capacity (n-LSB=1, no random start to maximize capacity)
            self.test_cases.append(
                TestCase("Capacity Test: waguri.png (Expected to FAIL)", 
                        str(self.cover_audio), str(waguri_png), False, False, 1, scenario="Scenario 2")
            )
        
        # Scenario 3: Various file types with random configurations
        print("[Scenario 3] Various file types with randomized configurations")
        test_files = [
            self.tests_dir / "sample_secret.txt",
            self.tests_dir / "waguri.png",
            self.tests_dir / "waguri.webp",
            self.tests_dir / "blokchein.pdf",
            self.tests_dir / "wagureng.zip",
        ]
        
        # Add any additional files found in tests directory
        for file_path in self.tests_dir.glob("*"):
            if file_path.is_file() and file_path.suffix not in ['.mp3'] and file_path not in test_files:
                test_files.append(file_path)
        
        # Filter existing files
        test_files = [f for f in test_files if f.exists()]
        
        for test_file in test_files:
            # Random configuration for each file type
            use_enc = random.choice([True, False])
            use_rand = random.choice([True, False])
            nlsb = random.randint(2, 4)  # Use 2-4 for better capacity
            
            test_name = f"Random Config: {test_file.suffix} - Enc={use_enc}, Rand={use_rand}, n-LSB={nlsb}"
            self.test_cases.append(
                TestCase(test_name, str(self.cover_audio), str(test_file), 
                        use_enc, use_rand, nlsb, scenario="Scenario 3")
            )
        
        print(f"\nTotal test cases generated: {len(self.test_cases)}")
    
    def run_test(self, test_case: TestCase):
        """Run a single test case"""
        print(f"\nRunning: {test_case.name}")
        print(f"  Secret file: {os.path.basename(test_case.secret_file)}")
        print(f"  Config: Encryption={test_case.use_encryption}, Random={test_case.use_random}, n-LSB={test_case.nlsb}")
        
        start_time = time.time()
        
        # Generate unique output file names
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        stego_file = self.output_dir / f"stego_{timestamp}.mp3"
        
        # Get original file size
        test_case.file_size = get_file_size(test_case.secret_file)
        
        # Generate key for encryption/random start
        key = f"testkey_{timestamp}"
        
        try:
            # Calculate original hash
            test_case.original_hash = calculate_md5(test_case.secret_file)
            
            # Embed
            print("  Embedding...")
            self.stego.embed_file(
                mp3_path=test_case.cover_file,
                payload_path=test_case.secret_file,
                out_path=str(stego_file),
                key=key,
                nlsb=test_case.nlsb,
                encrypt=test_case.use_encryption,
                random_start=test_case.use_random
            )
            
            # Calculate PSNR
            import numpy as np
            with open(test_case.cover_file, "rb") as f:
                original_bytes = f.read()
            with open(str(stego_file), "rb") as f:
                stego_bytes = f.read()
            L = min(len(original_bytes), len(stego_bytes))
            if L == 0:
                psnr = float("inf")
            else:
                diff = np.frombuffer(original_bytes[:L], dtype=np.uint8).astype(
                    np.int32
                ) - np.frombuffer(stego_bytes[:L], dtype=np.uint8).astype(np.int32)
                mse = float(np.mean(diff * diff)) if L > 0 else 0.0
                psnr = (
                    float("inf")
                    if mse == 0
                    else 10.0 * np.log10((255.0 * 255.0) / mse)
                )
            test_case.psnr = f"{psnr:.2f} dB"
            
            # Extract
            print("  Extracting...")
            extracted_path, size_bytes, status = self.stego.extract_file(
                mp3_path=str(stego_file),
                out_path=str(self.extracted_dir),
                key=key,
                restore_meta=True
            )
            
            # Calculate extracted hash
            test_case.extracted_hash = calculate_md5(extracted_path)
            
            # Check integrity
            if test_case.original_hash == test_case.extracted_hash:
                test_case.integrity = "✓ MATCH"
                test_case.result = "SUCCESS"
                print(f"  ✓ Test PASSED - Integrity verified")
            else:
                test_case.integrity = "✗ MISMATCH"
                test_case.result = "FAILED"
                test_case.error_message = "Hash mismatch"
                print(f"  ✗ Test FAILED - Hash mismatch")
            
            # Cleanup stego file
            try:
                os.remove(stego_file)
            except:
                pass
                
        except Exception as e:
            test_case.result = "ERROR"
            test_case.integrity = "N/A"
            test_case.error_message = str(e)[:100]  # Limit error message length
            print(f"  ✗ Test ERROR: {test_case.error_message}")
            
            # Cleanup on error
            try:
                if stego_file.exists():
                    os.remove(stego_file)
            except:
                pass
        
        test_case.execution_time = time.time() - start_time
        print(f"  Execution time: {test_case.execution_time:.2f}s")
    
    def run_all_tests(self):
        """Run all test cases"""
        print(f"\n{'='*80}")
        print(f"Starting Test Execution")
        print(f"{'='*80}")
        
        total = len(self.test_cases)
        for idx, test_case in enumerate(self.test_cases, 1):
            print(f"\n[Test {idx}/{total}]")
            self.run_test(test_case)
        
        print(f"\n{'='*80}")
        print(f"All Tests Completed")
        print(f"{'='*80}")
    
    def generate_report(self):
        """Generate comprehensive test report"""
        report_file = self.output_dir / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        # Calculate statistics
        total_tests = len(self.test_cases)
        success_count = sum(1 for t in self.test_cases if t.result == "SUCCESS")
        failed_count = sum(1 for t in self.test_cases if t.result == "FAILED")
        error_count = sum(1 for t in self.test_cases if t.result == "ERROR")
        
        with open(report_file, 'w', encoding='utf-8') as f:
            # Header
            f.write("="*100 + "\n")
            f.write(" "*30 + "AUDIO STEGANOGRAPHY TEST REPORT\n")
            f.write("="*100 + "\n\n")
            
            f.write(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Cover Audio: {self.cover_audio.name}\n")
            f.write(f"Total Tests: {total_tests}\n\n")
            
            # Summary Statistics
            f.write("-"*100 + "\n")
            f.write("TEST SUMMARY\n")
            f.write("-"*100 + "\n")
            f.write(f"✓ SUCCESS: {success_count} ({success_count/total_tests*100:.1f}%)\n")
            f.write(f"✗ FAILED:  {failed_count} ({failed_count/total_tests*100:.1f}%)\n")
            f.write(f"⚠ ERROR:   {error_count} ({error_count/total_tests*100:.1f}%)\n")
            f.write("-"*100 + "\n\n")
            
            # Detailed Results Table - Separated by Scenario
            f.write("="*130 + "\n")
            f.write("DETAILED TEST RESULTS\n")
            f.write("="*130 + "\n\n")
            
            # Group tests by scenario
            scenarios = {}
            for test in self.test_cases:
                scenario = test.scenario if test.scenario else "Other"
                if scenario not in scenarios:
                    scenarios[scenario] = []
                scenarios[scenario].append(test)
            
            # Print each scenario separately
            for scenario_name in ["Scenario 1", "Scenario 2", "Scenario 3"]:
                if scenario_name not in scenarios:
                    continue
                    
                f.write(f"\n{scenario_name.upper()}\n")
                f.write("-"*130 + "\n")
                
                # Table header
                f.write(f"{'No':<4} {'Test Name':<45} {'File':<18} {'Size':<10} {'Enc':<4} {'Rnd':<4} {'LSB':<4} {'PSNR':<12} {'Result':<9} {'Integrity':<11} {'Time':<7}\n")
                f.write("-"*130 + "\n")
                
                # Table rows
                scenario_tests = scenarios[scenario_name]
                for idx, test in enumerate(scenario_tests, 1):
                    data = test.to_dict()
                    test_name = data['name'][:43]  # Truncate if too long
                    secret_file = os.path.basename(test.secret_file)[:16]
                    
                    f.write(f"{idx:<4} {test_name:<45} {secret_file:<18} {data['file_size']:<10} "
                           f"{data['encryption']:<4} {data['random_start']:<4} {data['nlsb']:<4} "
                           f"{data['psnr']:<12} {data['result']:<9} {data['integrity']:<11} {data['execution_time']:<7}\n")
                
                f.write("-"*130 + "\n")
            
            f.write("\n")
            
            # Errors Details
            if error_count > 0:
                f.write("="*100 + "\n")
                f.write("ERROR DETAILS\n")
                f.write("="*100 + "\n\n")
                
                for idx, test in enumerate(self.test_cases, 1):
                    if test.result in ["ERROR", "FAILED"]:
                        f.write(f"[Test {idx}] {test.name}\n")
                        f.write(f"  File: {os.path.basename(test.secret_file)}\n")
                        f.write(f"  Status: {test.result}\n")
                        f.write(f"  Error: {test.error_message}\n\n")
            
            # Configuration Analysis
            f.write("="*100 + "\n")
            f.write("CONFIGURATION ANALYSIS\n")
            f.write("="*100 + "\n\n")
            
            # Success rate by configuration
            configs = {}
            for test in self.test_cases:
                config_key = f"Enc={test.use_encryption}, Rand={test.use_random}, LSB={test.nlsb}"
                if config_key not in configs:
                    configs[config_key] = {'total': 0, 'success': 0}
                configs[config_key]['total'] += 1
                if test.result == "SUCCESS":
                    configs[config_key]['success'] += 1
            
            f.write(f"{'Configuration':<40} {'Tests':<10} {'Success':<10} {'Rate':<10}\n")
            f.write("-"*70 + "\n")
            for config, stats in sorted(configs.items()):
                rate = stats['success'] / stats['total'] * 100 if stats['total'] > 0 else 0
                f.write(f"{config:<40} {stats['total']:<10} {stats['success']:<10} {rate:.1f}%\n")
            
            f.write("\n" + "="*100 + "\n")
            f.write("END OF REPORT\n")
            f.write("="*100 + "\n")
        
        print(f"\n✓ Test report saved to: {report_file}")
        return report_file
    
    def print_summary_table(self):
        """Print summary table to console"""
        print(f"\n{'='*130}")
        print("TEST RESULTS SUMMARY TABLE")
        print(f"{'='*130}\n")
        
        # Group tests by scenario
        scenarios = {}
        for test in self.test_cases:
            scenario = test.scenario if test.scenario else "Other"
            if scenario not in scenarios:
                scenarios[scenario] = []
            scenarios[scenario].append(test)
        
        # Print each scenario separately
        for scenario_name in ["Scenario 1", "Scenario 2", "Scenario 3"]:
            if scenario_name not in scenarios:
                continue
            
            print(f"\n{scenario_name.upper()}")
            print("-"*130)
            print(f"{'No':<4} {'Test Name':<40} {'File':<12} {'Config':<20} {'PSNR':<12} {'Result':<10} {'Integrity':<12}")
            print("-"*130)
            
            scenario_tests = scenarios[scenario_name]
            for idx, test in enumerate(scenario_tests, 1):
                test_name = test.name[:38]
                file_ext = Path(test.secret_file).suffix[:10]
                config = f"E={int(test.use_encryption)}|R={int(test.use_random)}|L={test.nlsb}"
                
                print(f"{idx:<4} {test_name:<40} {file_ext:<12} {config:<20} {test.psnr:<12} {test.result:<10} {test.integrity:<12}")
            
            print("-"*130)
        
        # Overall Statistics
        total = len(self.test_cases)
        success = sum(1 for t in self.test_cases if t.result == "SUCCESS")
        failed = sum(1 for t in self.test_cases if t.result == "FAILED")
        error = sum(1 for t in self.test_cases if t.result == "ERROR")
        
        print(f"\n{'='*130}")
        print(f"OVERALL STATISTICS")
        print(f"{'='*130}")
        print(f"Total: {total} | ✓ Success: {success} | ✗ Failed: {failed} | ⚠ Error: {error}")
        print(f"Success Rate: {success/total*100:.1f}%\n")
        print(f"{'='*130}\n")


def main():
    """Main execution function"""
    print("="*80)
    print(" "*20 + "AUDIO STEGANOGRAPHY TEST SUITE")
    print("="*80)
    print()
    print("Test Scenarios:")
    print("  1. All configuration combinations (encryption & random start) with sample_secret.txt")
    print("  2. Capacity overflow test with waguri.png")
    print("  3. Various file types (.txt, .png, .pdf, .zip, .webp, etc.) with random configs")
    print()
    print("Integrity Check: MD5 hash comparison (original vs extracted)")
    print("Cover Audio: cover.mp3")
    print()
    
    # Create test report instance
    report = TestReport()
    
    # Check if cover audio exists
    if not report.cover_audio.exists():
        print(f"ERROR: Cover audio file not found: {report.cover_audio}")
        return
    
    # Generate test cases
    report.generate_test_cases()
    
    # Confirm before running
    response = input(f"\nReady to run {len(report.test_cases)} test cases. Continue? (y/n): ")
    if response.lower() != 'y':
        print("Test execution cancelled.")
        return
    
    # Run all tests
    report.run_all_tests()
    
    # Generate report
    report_file = report.generate_report()
    
    # Print summary table to console
    report.print_summary_table()
    
    print(f"\n✓ Test execution completed!")
    print(f"✓ Detailed report saved to: {report_file}")
    print(f"✓ Extracted files saved to: {report.extracted_dir}")


if __name__ == "__main__":
    main()
