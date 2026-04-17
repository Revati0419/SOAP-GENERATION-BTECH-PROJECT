#!/bin/bash
# Monitor QLoRA training progress

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "              QLORA TRAINING MONITOR"
echo "═══════════════════════════════════════════════════════════════════"
echo ""

# Check if training log exists
if [ -f training_log.txt ]; then
    echo "📋 Latest training log (last 30 lines):"
    echo "───────────────────────────────────────────────────────────────────"
    tail -30 training_log.txt
    echo "───────────────────────────────────────────────────────────────────"
    echo ""
fi

# Check for output directory
if [ -d outputs/qlora_v1 ]; then
    echo "📁 Output directory contents:"
    ls -lh outputs/qlora_v1/
    echo ""
fi

# Check if training process is running
if pgrep -f "qlora_train.py" > /dev/null; then
    echo "✅ Training process is RUNNING"
else
    echo "⚠️  Training process is NOT running"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "💡 Tips:"
echo "   • Run this script anytime: bash scripts/monitor_training.sh"
echo "   • View full log: less training_log.txt"
echo "   • Follow live: tail -f training_log.txt"
echo ""
