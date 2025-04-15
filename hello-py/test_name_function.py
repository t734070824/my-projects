from name_function import get_formatted_name

def test_get_formatted_name():
    """Test for get_formatted_name function."""
    formatted_name = get_formatted_name('john', 'doe')
    assert formatted_name == 'John Doe', f"Expected 'John Doe', but got {formatted_name}"

    formatted_name = get_formatted_name('jane', 'smith')
    assert formatted_name == 'Jane Smith', f"Expected 'Jane Smith', but got {formatted_name}"

    formatted_name = get_formatted_name('alice', 'johnson')
    assert formatted_name == 'Alice Johnson', f"Expected 'Alice Johnson', but got {formatted_name}"



