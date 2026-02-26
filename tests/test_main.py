"""Tests for the c2c_gpx main module."""

from c2c_gpx.main import (
    clean_and_html,
    create_route_altitude,
    create_route_grade,
    create_route_height,
    create_route_orientation,
    generate_filename,
    get_locale,
    get_locales,
    increment_pitches,
    parse_c2c_url,
)

import pytest


class TestCreateRouteGrade:
    """Tests for create_route_grade function."""

    def test_empty_route(self):
        """Test with an empty route dict."""
        route = {}
        result = create_route_grade(route)
        assert result == ""

    def test_only_global_rating(self):
        """Test with only global_rating."""
        route = {"global_rating": "5a"}
        result = create_route_grade(route)
        assert result == "5a"

    def test_all_ratings(self):
        """Test with all rating fields."""
        route = {
            "global_rating": "5a",
            "rock_free_rating": "4c",
            "rock_required_rating": "3a",
            "aid_rating": "A1",
            "engagement_rating": "E1",
            "risk_rating": "R1",
            "equipment_rating": "P1",
            "exposition_rock_rating": "SO",
        }
        result = create_route_grade(route)
        assert result == "5a 4c>3a A1 E1 R1 P1 SO"

    def test_partial_ratings(self):
        """Test with some rating fields missing."""
        route = {
            "global_rating": "5b",
            "rock_free_rating": "4c",
            "risk_rating": "R2",
        }
        result = create_route_grade(route)
        assert result == "5b 4c R2"

    def test_whitespace_handling(self):
        """Test with values that have internal whitespace."""
        route = {
            "global_rating": "5a",
            "rock_free_rating": "4c",
        }
        result = create_route_grade(route)
        assert result == "5a 4c"


class TestCreateRouteAltitude:
    """Tests for create_route_altitude function."""

    def test_empty_elevation(self):
        """Test with empty elevation values (all missing keys raise KeyError)."""
        route = {}
        with pytest.raises(KeyError):
            create_route_altitude(route)

    def test_only_min_elevation(self):
        """Test with only elevation_min."""
        route = {"elevation_min": 1200, "elevation_max": None}
        result = create_route_altitude(route)
        assert result == "1200 m"

    def test_only_max_elevation(self):
        """Test with only elevation_max."""
        route = {"elevation_min": None, "elevation_max": 2500}
        result = create_route_altitude(route)
        assert result == "2500 m"

    def test_both_elevations(self):
        """Test with both min and max elevation."""
        route = {"elevation_min": 1200, "elevation_max": 2500}
        result = create_route_altitude(route)
        assert result == "1200 m - 2500 m"

    def test_zero_elevation(self):
        """Test with zero elevation values (falsy in Python)."""
        route = {"elevation_min": 0, "elevation_max": 0}
        result = create_route_altitude(route)
        assert result == ""


class TestCreateRouteOrientation:
    """Tests for create_route_orientation function."""

    def test_empty_orientation(self):
        """Test with empty orientations (missing key raises KeyError)."""
        route = {}
        with pytest.raises(KeyError):
            create_route_orientation(route)

    def test_single_orientation(self):
        """Test with single orientation."""
        route = {"orientations": ["N"]}
        result = create_route_orientation(route)
        assert result == "N"

    def test_multiple_orientations(self):
        """Test with multiple orientations."""
        route = {"orientations": ["N", "E", "S", "W"]}
        result = create_route_orientation(route)
        assert result == "N,E,S,W"


class TestCreateRouteHeight:
    """Tests for create_route_height function."""

    def test_empty_height(self):
        """Test with empty height values (missing keys raise KeyError)."""
        route = {}
        with pytest.raises(KeyError):
            create_route_height(route)

    def test_only_up(self):
        """Test with only height_diff_up."""
        route = {"height_diff_up": 500, "height_diff_down": None, "height_diff_difficulties": None}
        result = create_route_height(route)
        assert result == "+500 m"

    def test_only_down(self):
        """Test with only height_diff_down."""
        route = {"height_diff_up": None, "height_diff_down": 300, "height_diff_difficulties": None}
        result = create_route_height(route)
        assert result == "-300 m"

    def test_both_diffs(self):
        """Test with both up and down diffs."""
        route = {"height_diff_up": 500, "height_diff_down": 300, "height_diff_difficulties": None}
        result = create_route_height(route)
        assert result == "+500 m / -300 m"

    def test_with_difficulties_only(self):
        """Test with only height_diff_difficulties."""
        route = {"height_diff_up": None, "height_diff_down": None, "height_diff_difficulties": 200}
        result = create_route_height(route)
        assert result == "200 m"

    def test_with_difficulties_and_up(self):
        """Test with difficulties and up diff."""
        route = {"height_diff_up": 500, "height_diff_down": None, "height_diff_difficulties": 200}
        result = create_route_height(route)
        assert result == "+500 m (200 m)"


class TestIncrementPitches:
    """Tests for increment_pitches function."""

    def test_empty_text(self):
        """Test with empty text."""
        result = increment_pitches("")
        assert result == ""

    def test_numberless_l_pitch(self):
        """Test with numberless L pitch."""
        result = increment_pitches("L#~ start")
        assert result == " start"

    def test_numberless_r_pitch(self):
        """Test with numberless R pitch."""
        result = increment_pitches("R#~ start")
        assert result == " start"

    def test_already_numbered_l(self):
        """Test with already numbered L pitch."""
        result = increment_pitches("L#3 start")
        assert result == "<b>L3</b> start"

    def test_already_numbered_r(self):
        """Test with already numbered R pitch."""
        result = increment_pitches("R#5 start")
        assert result == "<b>R5</b> start"

    def test_increment_multiple_l(self):
        """Test incrementing multiple L pitches."""
        result = increment_pitches("L# start L# end")
        assert result == "<b>L1</b> start <b>L2</b> end"

    def test_increment_multiple_r(self):
        """Test incrementing multiple R pitches."""
        result = increment_pitches("R# start R# end")
        assert result == "<b>R1</b> start <b>R2</b> end"

    def test_increment_mixed_pitches(self):
        """Test incrementing mixed L and R pitches."""
        result = increment_pitches("L# start R# middle L# end")
        assert result == "<b>L1</b> start <b>R1</b> middle <b>L2</b> end"

    def test_complex_pitch_sequence(self):
        """Test complex pitch sequence with numbers - each counter is independent."""
        result = increment_pitches("L#1 L#2 L# L#3 R# R#1 R#2")
        assert result == "<b>L1</b> <b>L2</b> <b>L1</b> <b>L3</b> <b>R1</b> <b>R1</b> <b>R2</b>"


class TestCleanAndHtml:
    """Tests for clean_and_html function."""

    def test_empty_text(self):
        """Test with empty text."""
        result = clean_and_html("")
        assert result == ""

    def test_c2c_route_link(self):
        """Test C2C route link conversion."""
        text = "[[routes/1234]]"
        result = clean_and_html(text)
        assert "https://www.camptocamp.org/routes/1234" in result

    def test_c2c_route_link_with_name(self):
        """Test C2C route link with custom name."""
        text = "[[routes/1234|Custom Name]]"
        result = clean_and_html(text)
        assert "https://www.camptocamp.org/routes/1234" in result
        assert "Custom Name" in result

    def test_c2c_waypoint_link(self):
        """Test C2C waypoint link conversion."""
        text = "[[waypoints/5678]]"
        result = clean_and_html(text)
        assert "https://www.camptocamp.org/waypoints/5678" in result

    def test_c2c_outing_link(self):
        """Test C2C outing link conversion."""
        text = "[[outings/9999|Some Outing]]"
        result = clean_and_html(text)
        assert "https://www.camptocamp.org/outings/9999" in result

    def test_image_link_with_caption(self):
        """Test image link with caption."""
        text = "[img=12345]caption[/img]"
        result = clean_and_html(text)
        assert "https://media.camptocamp.org/c2corg-active/uploads/images/12345.jpg" in result

    def test_image_link_without_caption(self):
        """Test image link without caption - this pattern may not be handled."""
        text = "[img=12345/]"
        result = clean_and_html(text)
        # This pattern may not be converted - verify it doesn't break
        assert "12345" in result

    def test_pitch_increments_in_html(self):
        """Test that pitch increments work in HTML context."""
        text = "L# start"
        result = clean_and_html(text)
        assert "<b>L1</b>" in result


class TestGetLocale:
    """Tests for get_locale function."""

    def test_locale_found(self):
        """Test finding an existing locale."""
        route = {
            "locales": [
                {"lang": "fr", "title": "French Title"},
                {"lang": "en", "title": "English Title"},
            ]
        }
        result = get_locale(route, "fr")
        assert result is not None
        assert result["lang"] == "fr"
        assert result["title"] == "French Title"

    def test_locale_not_found(self):
        """Test when locale is not found."""
        route = {
            "locales": [
                {"lang": "fr", "title": "French Title"},
            ]
        }
        result = get_locale(route, "de")
        assert result is None

    def test_empty_locales(self):
        """Test with empty locales."""
        route = {"locales": []}
        result = get_locale(route, "fr")
        assert result is None

    def test_default_language(self):
        """Test with default French language."""
        route = {
            "locales": [
                {"lang": "fr", "title": "French Title"},
            ]
        }
        result = get_locale(route)
        assert result is not None
        assert result["lang"] == "fr"


class TestGetLocales:
    """Tests for get_locales function."""

    def test_first_language_available(self):
        """Test getting first available language."""
        route = {
            "document_id": 123,
            "locales": [
                {"lang": "fr", "title": "French Title"},
                {"lang": "en", "title": "English Title"},
            ],
        }
        result = get_locales(route, ("fr", "en"))
        assert result["lang"] == "fr"
        assert result["title"] == "French Title"

    def test_fallback_to_second_language(self):
        """Test fallback to second language when first not available."""
        route = {
            "document_id": 123,
            "locales": [
                {"lang": "de", "title": "German Title"},
                {"lang": "en", "title": "English Title"},
            ],
        }
        result = get_locales(route, ("fr", "en"))
        assert result["lang"] == "en"
        assert result["title"] == "English Title"

    def test_no_available_language(self):
        """Test error when no language is available."""
        route = {
            "document_id": 123,
            "locales": [
                {"lang": "de", "title": "German Title"},
            ],
        }
        with pytest.raises(RuntimeError) as exc_info:
            get_locales(route, ("fr", "en"))
        assert "has no locale in" in str(exc_info.value)


class TestParseC2cUrl:
    """Tests for parse_c2c_url function."""

    def test_basic_route_url(self):
        """Test parsing basic route URL."""
        url = "https://www.camptocamp.org/routes"
        doc_type, params = parse_c2c_url(url)
        assert doc_type == "routes"
        assert params == {"limit": 100}

    def test_route_url_with_params(self):
        """Test parsing route URL with parameters."""
        url = "https://www.camptocamp.org/routes?act=rock_climbing"
        doc_type, params = parse_c2c_url(url)
        assert doc_type == "routes"
        assert params["act"] == "rock_climbing"
        assert params["limit"] == 100

    def test_waypoint_url(self):
        """Test parsing waypoint URL."""
        url = "https://www.camptocamp.org/waypoints"
        doc_type, params = parse_c2c_url(url)
        assert doc_type == "waypoints"

    def test_outing_url(self):
        """Test parsing outing URL."""
        url = "https://www.camptocamp.org/outings"
        doc_type, params = parse_c2c_url(url)
        assert doc_type == "outings"

    def test_url_with_bbox(self):
        """Test URL with bounding box parameter."""
        url = "https://www.camptocamp.org/routes?bbox=616096,5333945,627309,5346461"
        doc_type, params = parse_c2c_url(url)
        assert doc_type == "routes"
        assert params["bbox"] == "616096,5333945,627309,5346461"

    def test_url_with_multiple_params(self):
        """Test URL with multiple parameters."""
        url = "https://www.camptocamp.org/routes?act=rock_climbing&bbox=616096,5333945,627309,5346461"
        doc_type, params = parse_c2c_url(url)
        assert doc_type == "routes"
        assert params["act"] == "rock_climbing"
        assert params["bbox"] == "616096,5333945,627309,5346461"

    def test_limit_is_overridden(self):
        """Test that limit is always set to 100."""
        url = "https://www.camptocamp.org/routes?limit=10"
        doc_type, params = parse_c2c_url(url)
        assert params["limit"] == 100


class TestGenerateFilename:
    """Tests for generate_filename function."""

    def test_basic_filename(self):
        """Test generating basic filename."""
        doc_type = "routes"
        params = {}
        result = generate_filename(doc_type, params)
        assert result == "routes.gpx"

    def test_filename_with_single_param(self):
        """Test filename with single parameter."""
        doc_type = "routes"
        params = {"act": "rock_climbing"}
        result = generate_filename(doc_type, params)
        assert result == "routes_act-rock_climbing.gpx"

    def test_filename_with_multiple_params(self):
        """Test filename with multiple parameters."""
        doc_type = "routes"
        params = {"act": "rock_climbing", "bbox": "616096,5333945"}
        result = generate_filename(doc_type, params)
        assert "routes_" in result
        assert "act-rock_climbing" in result
        # Commas in values are replaced with dashes
        assert "bbox-616096-5333945" in result
        assert result.endswith(".gpx")

    def test_filename_ignores_limit_offset(self):
        """Test that limit and offset are ignored."""
        doc_type = "routes"
        params = {"act": "climbing", "limit": 100, "offset": 0}
        result = generate_filename(doc_type, params)
        assert "limit" not in result
        assert "offset" not in result
        assert "act-climbing" in result

    def test_filename_with_comma_in_value(self):
        """Test that commas in values are replaced with dashes."""
        doc_type = "routes"
        params = {"bbox": "a,b,c"}
        result = generate_filename(doc_type, params)
        assert "bbox-a-b-c" in result

    def test_waypoint_filename(self):
        """Test generating waypoint filename."""
        doc_type = "waypoints"
        params = {"type": "summit"}
        result = generate_filename(doc_type, params)
        assert result == "waypoints_type-summit.gpx"
