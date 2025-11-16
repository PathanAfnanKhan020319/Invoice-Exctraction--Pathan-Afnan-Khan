"""
Quick run script for invoice extraction pipeline
Usage: python run_pipeline.py [directory] [--strategy auto|ocr_only|llm_only|both]
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.append(str(Path(__file__).parent))

from src.pipeline import InvoiceExtractionPipeline
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def main():
    """Main execution function"""
    
    # Parse arguments
    parser = argparse.ArgumentParser(
        description='Process invoice files and extract structured data'
    )
    parser.add_argument(
        'directory',
        type=str,
        nargs='?',
        default='data/raw',
        help='Directory containing invoice files (default: data/raw)'
    )
    parser.add_argument(
        '--strategy',
        type=str,
        choices=['auto', 'ocr_only', 'llm_only', 'both'],
        default='auto',
        help='Extraction strategy (default: auto)'
    )
    parser.add_argument(
        '--parallel',
        action='store_true',
        help='Enable parallel processing'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )
    
    args = parser.parse_args()
    
    print("="*70)
    print("INVOICE EXTRACTION PIPELINE")
    print("="*70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Directory: {args.directory}")
    print(f"Strategy: {args.strategy}")
    print(f"Parallel: {args.parallel}")
    print("="*70)
    print()
    
    # Check if directory exists
    if not Path(args.directory).exists():
        print(f"Error: Directory '{args.directory}' not found")
        print("Please create the directory and add invoice files, or specify a different path")
        return 1
    
    try:
        # Initialize pipeline
        print("Initializing pipeline...")
        pipeline = InvoiceExtractionPipeline(config_path=args.config)
        print("✓ Pipeline initialized")
        print()
        
        # Process directory
        print(f"Processing invoices in {args.directory}...")
        print("-" * 70)
        
        results = pipeline.process_directory(
            directory=args.directory,
            strategy=args.strategy,
            parallel=args.parallel
        )
        
        print("-" * 70)
        print()
        
        # Display results
        if results:
            print("="*70)
            print("EXTRACTION COMPLETE")
            print("="*70)
            print(f"✓ Successfully processed {len(results)} invoice(s)")
            print()
            
            # Get statistics
            stats = pipeline.get_statistics()
            print("Database Statistics:")
            print(f"  Total invoices: {stats['total_invoices']}")
            print(f"  Total amount: ${stats['total_amount']:,.2f}")
            print(f"  Unique vendors: {stats['unique_vendors']}")
            print()
            
            # Show spending by vendor
            spending = pipeline.get_spending_by_vendor()
            print("Top 5 Vendors by Spend:")
            for i, row in spending.head(5).iterrows():
                print(f"  {i+1}. {row['vendor_name']}: ${row['total_spend']:,.2f} ({row['invoice_count']} invoices)")
            print()
            
            # Export summary
            print("Outputs saved to:")
            print("  - Database: outputs/invoices.db")
            print("  - JSON: outputs/extracted_data.json")
            print("  - CSV: outputs/extracted_data.csv")
            print()
            
            print("Next steps:")
            print("  - View dashboard: streamlit run streamlit_dashboard.py")
            print("  - Query data: See notebooks/02_extraction_pipeline.ipynb")
            print("="*70)
            
            return 0
        else:
            print("⚠ No invoices were successfully processed")
            print("Check the logs for error details")
            return 1
            
    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\nError: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)