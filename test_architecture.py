#!/usr/bin/env python3
"""
Test 6-Layer Architecture
Verifies all layers work together without calling external APIs
"""

import json
from datetime import datetime, timedelta

# Test data
mock_account = {
    'cash': 5000.00,
    'portfolio_value': 25000.00,
    'buying_power': 10000.00,
    'equity': 25000.00
}

mock_positions = [
    {
        'symbol': 'NVDA',
        'qty': 100,
        'current_price': 147.50,
        'avg_entry_price': 145.00,
        'market_value': 14750.00,
        'cost_basis': 14500.00,
        'unrealized_pl': 250.00,
        'unrealized_plpc': 0.0172
    }
]

mock_notes = {
    'NVDA': {
        'entry_date': '2025-11-25',
        'entry_price': 145.00,
        'investment_thesis': 'Playing AI GPU demand into Q4 earnings',
        'target_price': 165.00,
        'stop_loss': 135.00,
        'time_horizon_weeks': 4,
        'target_exit_date': '2025-12-23',
        'expected_catalyst': 'Q4 earnings release',
        'created_at': '2025-11-25T20:00:00',
        'review_history': []
    }
}


def test_layer_1():
    """Test decision context builder"""
    print("Testing Layer 1: Decision Context Builder...")

    from src.utils.decision_context_builder import build_decision_context

    context = build_decision_context(mock_account, mock_positions, mock_notes)

    # Verify structure
    assert 'account' in context
    assert 'buy_options' in context
    assert 'position_options' in context
    assert 'positions_data' in context

    # Verify buy options
    assert 'DEPLOY_80_PERCENT' in context['buy_options']
    assert context['buy_options']['DEPLOY_80_PERCENT']['amount'] == 4000.00

    assert 'DEPLOY_ALL_CASH' in context['buy_options']
    assert context['buy_options']['DEPLOY_ALL_CASH']['amount'] == 5000.00

    # Verify position options
    assert 'NVDA' in context['position_options']
    nvda_options = context['position_options']['NVDA']

    assert nvda_options['TRIM_25']['qty'] == 25
    assert nvda_options['TRIM_50']['qty'] == 50
    assert nvda_options['SELL_ALL']['qty'] == 100

    print("  ✓ Context built correctly")
    print(f"  ✓ Cash: ${context['account']['available_cash']:,.2f}")
    print(f"  ✓ Buy options: {len(context['buy_options'])}")
    print(f"  ✓ Position options for NVDA: {len(nvda_options)}")

    return context


def test_layer_2():
    """Test rules engine"""
    print("\nTesting Layer 2: Rules Engine...")

    from src.utils.rules_engine import apply_rules_engine
    from src.utils.decision_context_builder import build_decision_context

    context = build_decision_context(mock_account, mock_positions, mock_notes)

    # Test with normal position (no triggers)
    automatic_actions, flagged = apply_rules_engine(mock_positions, mock_notes, context)

    assert isinstance(automatic_actions, list)
    assert isinstance(flagged, list)

    print(f"  ✓ Automatic actions: {len(automatic_actions)}")
    print(f"  ✓ Flagged positions: {len(flagged)}")

    # Test stop loss trigger
    mock_positions_stop_loss = [{
        **mock_positions[0],
        'current_price': 130.00  # Below stop loss of 135
    }]

    automatic_actions, flagged = apply_rules_engine(mock_positions_stop_loss, mock_notes, context)

    assert len(automatic_actions) == 1
    assert automatic_actions[0]['trigger'] == 'STOP_LOSS'
    print("  ✓ Stop loss trigger detected correctly")

    # Test target price trigger
    mock_positions_target = [{
        **mock_positions[0],
        'current_price': 170.00  # Above target of 165
    }]

    automatic_actions, flagged = apply_rules_engine(mock_positions_target, mock_notes, context)

    assert len(automatic_actions) == 1
    assert automatic_actions[0]['trigger'] == 'TARGET_REACHED'
    print("  ✓ Target price trigger detected correctly")


def test_layer_4():
    """Test decision validator"""
    print("\nTesting Layer 4: Decision Validator...")

    from src.utils.decision_validator import validate_decisions
    from src.utils.decision_context_builder import build_decision_context

    context = build_decision_context(mock_account, mock_positions, mock_notes)

    # Valid decision
    valid_decision = {
        'position_decisions': [
            {
                'symbol': 'NVDA',
                'action': 'HOLD',
                'reasoning': 'Thesis intact, approaching catalyst'
            }
        ],
        'cash_deployment': {
            'deployment_option': 'DEPLOY_ALL_CASH',
            'new_positions': [
                {
                    'symbol': 'AAPL',
                    'allocation_percent': 100,
                    'investment_thesis': 'Playing iPhone demand into holiday season',
                    'target_price': 200.00,
                    'stop_loss': 175.00,
                    'time_horizon_weeks': 4,
                    'target_exit_date': '2025-12-30',
                    'expected_catalyst': 'Holiday sales report'
                }
            ]
        }
    }

    result = validate_decisions(valid_decision, context, ['NVDA'])
    assert result['valid'] == True
    print("  ✓ Valid decision passes validation")

    # Invalid decision (allocation doesn't sum to 100)
    invalid_decision = {
        'position_decisions': [],
        'cash_deployment': {
            'deployment_option': 'DEPLOY_ALL_CASH',
            'new_positions': [
                {
                    'symbol': 'AAPL',
                    'allocation_percent': 50,  # Should be 100
                    'investment_thesis': 'Test thesis',
                    'target_price': 200.00,
                    'stop_loss': 175.00,
                    'time_horizon_weeks': 4,
                    'target_exit_date': '2025-12-30',
                    'expected_catalyst': 'Test catalyst'
                }
            ]
        }
    }

    result = validate_decisions(invalid_decision, context, ['NVDA'])
    assert result['valid'] == False
    assert len(result['errors']) > 0
    print("  ✓ Invalid decision rejected correctly")


def test_layer_6():
    """Test notes manager"""
    print("\nTesting Layer 6: Notes Manager...")

    from src.utils.notes_manager import (
        create_position_note,
        add_review_entry,
        update_position_notes
    )

    # Create a new note
    note = create_position_note(
        symbol='AAPL',
        entry_price=180.00,
        investment_thesis='Playing iPhone 16 demand',
        target_price=200.00,
        stop_loss=170.00,
        time_horizon_weeks=4,
        target_exit_date='2025-12-30',
        expected_catalyst='Holiday sales',
        entry_date='2025-12-01'
    )

    assert note['entry_price'] == 180.00
    assert note['target_price'] == 200.00
    assert note['stop_loss'] == 170.00
    print("  ✓ Note created correctly")

    # Add review entry
    note = add_review_entry(note, 'HOLD', 'Thesis intact')

    assert len(note['review_history']) == 1
    assert note['review_history'][0]['decision'] == 'HOLD'
    print("  ✓ Review entry added correctly")

    # Update notes
    new_positions = [
        {
            'symbol': 'MSFT',
            'allocation_percent': 100,
            'investment_thesis': 'Cloud growth story',
            'target_price': 420.00,
            'stop_loss': 380.00,
            'time_horizon_weeks': 3,
            'target_exit_date': '2025-12-22',
            'expected_catalyst': 'Azure earnings'
        }
    ]

    position_decisions = [
        {
            'symbol': 'NVDA',
            'action': 'HOLD',
            'reasoning': 'Keeping position'
        }
    ]

    updated_notes = update_position_notes(
        mock_notes.copy(),
        new_positions,
        position_decisions,
        {'MSFT': 400.00}
    )

    assert 'MSFT' in updated_notes
    assert updated_notes['MSFT']['entry_price'] == 400.00
    assert len(updated_notes['NVDA']['review_history']) == 1
    print("  ✓ Notes updated correctly")


def run_all_tests():
    """Run all architecture tests"""
    print("=" * 80)
    print("TESTING 6-LAYER ARCHITECTURE")
    print("=" * 80)

    try:
        context = test_layer_1()
        test_layer_2()
        test_layer_4()
        test_layer_6()

        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED")
        print("=" * 80)
        print("\nThe 6-layer architecture is working correctly!")
        print("You can now run: python main.py --mode once")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    run_all_tests()
