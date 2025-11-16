"""
Streamlit Dashboard for Invoice Data Exploration
Run with: streamlit run streamlit_dashboard.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import sys
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()


# Add src to path
sys.path.append(str(Path(__file__).parent))

from src.pipeline import InvoiceExtractionPipeline
from src.models import DatabaseManager

# Page configuration
st.set_page_config(
    page_title="Invoice Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'pipeline' not in st.session_state:
    st.session_state.pipeline = InvoiceExtractionPipeline()

pipeline = st.session_state.pipeline

# Sidebar
st.sidebar.title("📊 Navigation")
page = st.sidebar.radio("Go to", ["Dashboard", "Upload & Process", "Query Invoices", "Analytics"])

# Main content
if page == "Dashboard":
    st.markdown('<p class="main-header">📈 Invoice Analytics Dashboard</p>', unsafe_allow_html=True)
    st.markdown("---")
    
    # Get statistics
    stats = pipeline.get_statistics()
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Total Invoices",
            value=f"{stats['total_invoices']:,}",
            delta=None
        )
    
    with col2:
        st.metric(
            label="Total Amount",
            value=f"${stats['total_amount']:,.2f}",
            delta=None
        )
    
    with col3:
        st.metric(
            label="Unique Vendors",
            value=stats['unique_vendors'],
            delta=None
        )
    
    with col4:
        avg_amount = stats['total_amount'] / stats['total_invoices'] if stats['total_invoices'] > 0 else 0
        st.metric(
            label="Avg Invoice",
            value=f"${avg_amount:,.2f}",
            delta=None
        )
    
    st.markdown("---")
    
    # Get all data
    df = pipeline.export_all_data()
    
    if len(df) > 0:
        # Convert date column
        df['invoice_date'] = pd.to_datetime(df['invoice_date'])
        
        # Two columns for charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Top 10 Vendors by Spend")
            spending_df = pipeline.get_spending_by_vendor()
            top_vendors = spending_df.nlargest(10, 'total_spend')
            
            fig = px.bar(
                top_vendors,
                x='total_spend',
                y='vendor_name',
                orientation='h',
                labels={'total_spend': 'Total Spend ($)', 'vendor_name': 'Vendor'},
                color='total_spend',
                color_continuous_scale='Blues'
            )
            fig.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("📅 Invoices Over Time")
            monthly = df.groupby(df['invoice_date'].dt.to_period('M')).size().reset_index()
            monthly.columns = ['month', 'count']
            monthly['month'] = monthly['month'].astype(str)
            
            fig = px.line(
                monthly,
                x='month',
                y='count',
                markers=True,
                labels={'month': 'Month', 'count': 'Number of Invoices'}
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        # Full width chart
        st.subheader("💰 Invoice Amount Distribution")
        fig = px.histogram(
            df,
            x='total_amount',
            nbins=30,
            labels={'total_amount': 'Invoice Amount ($)'},
            color_discrete_sequence=['#1f77b4']
        )
        fig.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        # Recent invoices table
        st.subheader("📋 Recent Invoices")
        recent = df.nlargest(10, 'invoice_date')[['invoice_number', 'vendor_name', 'invoice_date', 'total_amount']]
        st.dataframe(recent, use_container_width=True)
    
    else:
        st.info("No invoices in database yet. Upload and process some invoices to see analytics!")

elif page == "Upload & Process":
    st.title("📤 Upload & Process Invoices")
    st.markdown("---")
    
    # File uploader
    uploaded_files = st.file_uploader(
        "Upload invoice files (PDF, PNG, JPG, JPEG, TIFF)",
        type=['pdf', 'png', 'jpg', 'jpeg', 'tiff'],
        accept_multiple_files=True
    )
    
    if uploaded_files:
        st.write(f"Uploaded {len(uploaded_files)} file(s)")
        
        # Extraction strategy
        strategy = st.selectbox(
            "Select extraction strategy",
            ["auto", "ocr_only", "llm_only", "both"],
            help="Auto: Try OCR first, use LLM if confidence is low"
        )
        
        if st.button("🚀 Process Invoices"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            results = []
            
            for i, uploaded_file in enumerate(uploaded_files):
                status_text.text(f"Processing {uploaded_file.name}...")
                
                # Save uploaded file temporarily
                temp_path = f"data/temp/{uploaded_file.name}"
                Path("data/temp").mkdir(parents=True, exist_ok=True)
                
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                # Process file
                try:
                    data = pipeline.process_file(temp_path, strategy=strategy)
                    if data:
                        results.append(data)
                        status_text.success(f"✓ Processed {uploaded_file.name}")
                    else:
                        status_text.error(f"✗ Failed to process {uploaded_file.name}")
                except Exception as e:
                    status_text.error(f"✗ Error processing {uploaded_file.name}: {str(e)}")
                
                progress_bar.progress((i + 1) / len(uploaded_files))
            
            # Show results
            st.success(f"Processing complete! Successfully processed {len(results)} invoices.")
            
            if results:
                st.subheader("Extracted Data")
                results_df = pd.DataFrame(results)
                display_cols = ['invoice_number', 'vendor_name', 'invoice_date', 'total_amount', 'confidence_score']
                st.dataframe(results_df[display_cols], use_container_width=True)

elif page == "Query Invoices":
    st.title("🔍 Query Invoices")
    st.markdown("---")
    
    # Query options
    col1, col2 = st.columns(2)
    
    with col1:
        # Get all vendors
        df = pipeline.export_all_data()
        if len(df) > 0:
            vendors = ["All"] + sorted(df['vendor_name'].unique().tolist())
            selected_vendor = st.selectbox("Select Vendor", vendors)
        else:
            st.info("No vendors in database yet")
            selected_vendor = "All"
    
    with col2:
        date_range = st.date_input(
            "Date Range",
            value=(date.today() - timedelta(days=365), date.today())
        )
    
    if st.button("🔍 Search"):
        if selected_vendor == "All":
            if len(date_range) == 2:
                results = pipeline.query_invoices(start_date=date_range[0], end_date=date_range[1])
            else:
                results = pipeline.export_all_data()
        else:
            if len(date_range) == 2:
                results = pipeline.query_invoices(
                    vendor=selected_vendor,
                    start_date=date_range[0],
                    end_date=date_range[1]
                )
            else:
                results = pipeline.query_invoices(vendor=selected_vendor)
        
        st.subheader(f"Found {len(results)} invoice(s)")
        
        if len(results) > 0:
            # Display summary
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Invoices", len(results))
            with col2:
                st.metric("Total Amount", f"${results['total_amount'].sum():,.2f}")
            with col3:
                st.metric("Average Amount", f"${results['total_amount'].mean():,.2f}")
            
            # Display table
            st.dataframe(results, use_container_width=True)
            
            # Download button
            csv = results.to_csv(index=False)
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name="invoice_query_results.csv",
                mime="text/csv"
            )

elif page == "Analytics":
    st.title("📊 Advanced Analytics")
    st.markdown("---")
    
    df = pipeline.export_all_data()
    
    if len(df) > 0:
        df['invoice_date'] = pd.to_datetime(df['invoice_date'])
        
        # Vendor spending analysis
        st.subheader("Vendor Spending Analysis")
        spending_df = pipeline.get_spending_by_vendor()
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Pie chart
            fig = px.pie(
                spending_df.nlargest(10, 'total_spend'),
                values='total_spend',
                names='vendor_name',
                title='Top 10 Vendors by Spend'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.dataframe(
                spending_df.nlargest(10, 'total_spend'),
                use_container_width=True
            )
        
        # Monthly trends
        st.subheader("Monthly Spending Trends")
        df['month'] = df['invoice_date'].dt.to_period('M')
        monthly_spend = df.groupby('month')['total_amount'].sum().reset_index()
        monthly_spend['month'] = monthly_spend['month'].astype(str)
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=monthly_spend['month'],
            y=monthly_spend['total_amount'],
            mode='lines+markers',
            name='Monthly Spend',
            line=dict(color='#1f77b4', width=3)
        ))
        fig.update_layout(
            xaxis_title='Month',
            yaxis_title='Total Spend ($)',
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Confidence analysis
        if 'confidence_score' in df.columns:
            st.subheader("Extraction Quality Analysis")
            
            col1, col2 = st.columns(2)
            
            with col1:
                avg_conf = df['confidence_score'].mean()
                st.metric("Average Confidence", f"{avg_conf:.1%}")
                
                fig = px.histogram(
                    df,
                    x='confidence_score',
                    nbins=20,
                    title='Distribution of Confidence Scores'
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Confidence by extraction method
                if 'extraction_method' in df.columns:
                    method_conf = df.groupby('extraction_method')['confidence_score'].mean()
                    st.dataframe(method_conf, use_container_width=True)
    
    else:
        st.info("No data available for analytics. Process some invoices first!")

# Footer
st.sidebar.markdown("---")
st.sidebar.info(
    "💡 **Tip:** Upload invoices to get started with extraction and analysis!"
)   