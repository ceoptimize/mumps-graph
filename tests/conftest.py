"""Pytest configuration and fixtures."""

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def sample_dd_lines():
    """Provide sample DD.zwr lines for testing."""
    return [
        'GT.M 26-MAR-2018 11:45:50 ZWR',
        '^DD(0,0)="ATTRIBUTE^N^999^41"',
        '^DD(2,0)="PATIENT^DPT^^200^200I^^"',
        '^DD(2,.01,0)="NAME^RF^^0;1^K:$L(X)>30!($L(X)<3) X"',
        '^DD(2,.02,0)="SEX^S^^0;2^Q"',
        '^DD(2,.03,0)="DATE OF BIRTH^D^^0;3^S %DT="EX" D ^%DT S X=Y K:Y<1 X"',
        '^DD(2,.09,0)="SOCIAL SECURITY NUMBER^F^^0;9^K:$L(X)>10!($L(X)<9) X"',
        '^DD(2,.1,0)="SERVICE CONNECTED?^S^^0;10^Q"',
        '^DD(2,.11,0)="DATE OF DEATH^D^^.35;1^S %DT="EX" D ^%DT S X=Y K:Y<1 X"',
        '^DD(2,.301,0)="SERVICE CONNECTED PERCENTAGE^NJ3,0^^.3;1^K:+X\'=X!(X>100)!(X<0)!(X?.E1"."1N.N) X"',
        '^DD(2,1901,0)="PROVIDER^P200\'^VA(200,^^DPT(^K:+X\'=X!(X>999999)!(X<1)!(X?.E1"."1N.N) X"',
        '^DD(200,0)="NEW PERSON^VA(200,^^200I^6006^6006"',
        '^DD(200,.01,0)="NAME^RFX^^0;1^K:$L(X)>35!($L(X)<3) X"',
    ]


@pytest.fixture
def sample_packages_csv():
    """Provide sample Packages.csv content."""
    return """Directory Name,Package Name,Prefixes,VDL ID,File Numbers Low,File Numbers High
Accounts Receivable,Accounts Receivable,PRC PRCA,36,430,430.9
Adverse Reaction Tracking,Adverse Reaction Tracking,GMRA,120,120,120.9
Automated Information Collection System,AICS,AQAO,129,155,155.99
Bar Code Medication Administration,BCMA,PSB,197,53.7,53.799
Beneficiary Travel,Beneficiary Travel,DGBT,181,392,392.99
Clinical Case Registries,CCR,ROR,195,798,799.9
Clinical Monitoring System,CMS,QAC,162,738,738.99
Clinical Procedures,Clinical Procedures,MD,164,702,704.999
Clinical Reminders,Clinical Reminders,PXRM,127,800,813.7
,,,,,
VA FileMan,VA FileMan,DI DIA DD DM,5,0.2,1.99999
,,,,,"""


@pytest.fixture
def mock_neo4j_connection():
    """Provide mock Neo4j connection for testing."""
    mock_conn = MagicMock()
    mock_conn.connect.return_value = True
    mock_conn.test_connection.return_value = True
    mock_conn.execute_query.return_value = [{"count": 0}]
    mock_conn.get_database_info.return_value = {
        "nodes": {"Package": 10, "File": 100, "Field": 1000},
        "relationships": {"CONTAINS_FIELD": 1000, "CONTAINS_FILE": 100},
        "total_nodes": 1110,
        "total_relationships": 1100,
    }
    return mock_conn


@pytest.fixture
def sample_zwr_file(tmp_path):
    """Create a temporary ZWR file for testing."""
    zwr_file = tmp_path / "test_dd.zwr"
    content = """GT.M 26-MAR-2018 11:45:50 ZWR
^DD(0,0)="ATTRIBUTE^N^999^41"
^DD(2,0)="PATIENT^DPT^^200^200I^^"
^DD(2,.01,0)="NAME^RF^^0;1^K:$L(X)>30!($L(X)<3) X"
^DD(2,.02,0)="SEX^S^^0;2^Q"
^DD(2,.03,0)="DATE OF BIRTH^D^^0;3^S %DT="EX" D ^%DT S X=Y K:Y<1 X"
^DD(200,0)="NEW PERSON^VA(200,^^200I^6006^6006"
^DD(200,.01,0)="NAME^RFX^^0;1^K:$L(X)>35!($L(X)<3) X"
^DD(200,1,0)="INITIAL^F^^0;2^K:$L(X)>5!($L(X)<1) X"
"""
    zwr_file.write_text(content)
    return zwr_file


@pytest.fixture
def sample_csv_file(tmp_path):
    """Create a temporary CSV file for testing."""
    csv_file = tmp_path / "test_packages.csv"
    content = """Directory Name,Package Name,Prefixes,VDL ID,File Numbers Low,File Numbers High
Accounts Receivable,Accounts Receivable,PRC PRCA,36,430,430.9
Adverse Reaction Tracking,Adverse Reaction Tracking,GMRA,120,120,120.9
VA FileMan,VA FileMan,DI DIA DD DM,5,0.2,1.99999
"""
    csv_file.write_text(content)
    return csv_file
