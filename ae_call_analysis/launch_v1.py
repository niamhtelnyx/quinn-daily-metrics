#!/usr/bin/env python3
"""
Launch V1 - Automated setup for Fellow Call Intelligence Cron Job
"""

import os
import subprocess
import sys
from datetime import datetime

def run_command(cmd, description):
    """Run a command and return success status"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"   ✅ Success")
        return True
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Failed: {e}")
        if e.stdout:
            print(f"      Output: {e.stdout}")
        if e.stderr:
            print(f"      Error: {e.stderr}")
        return False

def setup_environment():
    """Setup environment and directories"""
    print("📁 Setting up environment...")
    
    # Create logs directory
    os.makedirs('logs', exist_ok=True)
    print("   ✅ Created logs directory")
    
    # Make scripts executable
    scripts = ['fellow_cron_job.py', 'setup_cron_v1.sh', 'test_v1_components.py']
    for script in scripts:
        if os.path.exists(script):
            os.chmod(script, 0o755)
            print(f"   ✅ Made {script} executable")
    
    return True

def test_system():
    """Run component validation"""
    print("🧪 Running system validation...")
    
    try:
        result = subprocess.run([sys.executable, 'test_v1_components.py'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("   ✅ All components validated")
            return True
        else:
            print("   ❌ Component validation failed")
            print(result.stdout)
            return False
            
    except Exception as e:
        print(f"   ❌ Validation error: {e}")
        return False

def create_env_file():
    """Create .env file with configuration"""
    print("🔧 Creating environment configuration...")
    
    current_dir = os.getcwd()
    fellow_key = os.getenv('FELLOW_API_KEY', 'your_fellow_api_key_here')
    
    env_content = f"""# Fellow Call Intelligence V1 Configuration
# Generated: {datetime.now().isoformat()}

# Fellow API Configuration
FELLOW_API_KEY={fellow_key}

# Database Configuration  
DATABASE_PATH={current_dir}/ae_call_analysis.db

# Cron Configuration
CRON_LOG_PATH={current_dir}/logs/cron.log

# Python path
PYTHONPATH={current_dir}

# Optional: Enhanced analysis (add your keys)
# OPENAI_API_KEY=sk-proj-your-openai-key
# ANTHROPIC_API_KEY=sk-ant-your-claude-key

# Optional: Slack integration (add your webhook)
# SLACK_WEBHOOK_URL=https://hooks.slack.com/your-webhook
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("   ✅ Created .env file")
    return True

def show_cron_setup():
    """Show crontab setup instructions"""
    current_dir = os.getcwd()
    
    print("\n📅 CRONTAB SETUP INSTRUCTIONS")
    print("=" * 35)
    print()
    print("1️⃣ Open crontab editor:")
    print("   crontab -e")
    print()
    print("2️⃣ Add this line (30-minute intervals):")
    print(f"   */30 * * * * cd {current_dir} && source .env && python3 fellow_cron_job.py >> logs/cron.log 2>&1")
    print()
    print("3️⃣ Save and exit")
    print()
    
    return True

def run_test_cycle():
    """Run a test cron cycle"""
    print("🧪 Running test cron cycle...")
    
    try:
        # Source environment and run
        env = os.environ.copy()
        env['FELLOW_API_KEY'] = os.getenv('FELLOW_API_KEY', 'your_fellow_api_key_here')
        
        result = subprocess.run([sys.executable, 'fellow_cron_job.py'], 
                              env=env, capture_output=True, text=True, timeout=120)
        
        print("   📋 Test output:")
        print("   " + "\n   ".join(result.stdout.split('\n')[:20]))
        
        if result.returncode == 0:
            print("   ✅ Test cycle completed successfully")
            return True
        else:
            print("   ⚠️ Test cycle had issues")
            if result.stderr:
                print(f"   Error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("   ⚠️ Test cycle timed out (may be waiting for Fellow API)")
        return False
    except Exception as e:
        print(f"   ❌ Test cycle error: {e}")
        return False

def show_monitoring_commands():
    """Show monitoring commands"""
    print("\n📊 MONITORING COMMANDS")
    print("=" * 25)
    print()
    print("📝 View cron logs:")
    print("   tail -f logs/cron.log")
    print()
    print("🗃️ Check cron runs:")
    print("   sqlite3 ae_call_analysis.db 'SELECT * FROM cron_runs ORDER BY run_timestamp DESC LIMIT 5'")
    print()
    print("📞 Check processed calls:")
    print("   sqlite3 ae_call_analysis.db 'SELECT id, prospect_name, processed_by_enhanced FROM calls ORDER BY created_at DESC LIMIT 5'")
    print()

def main():
    """Main launch sequence"""
    print("🚀 LAUNCHING V1 - FELLOW CALL INTELLIGENCE CRON JOB")
    print("=" * 60)
    print()
    
    steps = [
        ("Setup Environment", setup_environment),
        ("Create Configuration", create_env_file),
        ("Validate System", test_system),
    ]
    
    for step_name, step_func in steps:
        print(f"{'='*20}")
        if not step_func():
            print(f"\n❌ Launch failed at: {step_name}")
            sys.exit(1)
        print()
    
    # Optional test cycle
    print("="*20)
    print("🧪 Optional: Run test cycle? (y/n): ", end="", flush=True)
    try:
        response = input().strip().lower()
        if response == 'y':
            run_test_cycle()
    except KeyboardInterrupt:
        print("\nSkipped test cycle")
    
    print("\n" + "="*60)
    print("🎉 V1 LAUNCH COMPLETE!")
    print()
    print("✅ SYSTEM READY:")
    print("   • Fellow API integration configured")
    print("   • Enhanced call processing pipeline ready")
    print("   • Database and tracking setup")
    print("   • Cron job script prepared")
    print()
    
    show_cron_setup()
    show_monitoring_commands()
    
    print("🎯 NEXT STEPS:")
    print("1. Set up crontab (instructions above)")
    print("2. Monitor first few runs")
    print("3. Validate Slack alerts")
    print("4. Gather stakeholder feedback")
    print()
    print("📋 For help: cat LAUNCH_V1.md")
    print()
    print("🚀 Your Fellow Call Intelligence V1 is ready to launch!")

if __name__ == "__main__":
    main()