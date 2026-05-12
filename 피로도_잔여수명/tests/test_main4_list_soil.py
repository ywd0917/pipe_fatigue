"""
main4_list_soil.py 테스트
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.main4_list_soil import (
    handle_search_mode,
    main,
    print_lithoidx_info,
    print_summary_statistics,
    save_to_csv,
)


@pytest.fixture
def mock_analysis_df():
    """분석 결과 DataFrame 모킹"""
    data = {
        "rank": [1, 2, 3],
        "lithoidx": [3, 2, 1],
        "lithoname": ["현무암", "편마암", "화강암"],
        "count": [4, 2, 3],
        "total_area": [295.0, 550.0, 450.0],
        "avg_area": [73.75, 275.0, 150.0],
        "total_length": [139.0, 135.0, 150.0],
        "unique_ages": [2, 1, 2],
        "ages": [
            "신생대 제4기(3), 중생대 백악기(1)",
            "선캄브리아시대(2)",
            "중생대 백악기(2), 중생대 쥐라기(1)",
        ],
        "map_count": [2, 2, 2],
        "maps": ["강릉, 속초", "강릉, 대전", "대전, 서울"],
    }
    return pd.DataFrame(data)


@pytest.fixture
def mock_lithoidx_stats():
    """LithoidxStatistics 모킹"""
    from src.soil_loader import LithoidxStatistics

    return LithoidxStatistics(
        total_lithoidx=3,
        total_objects=9,
        total_area=1295.0,
        avg_objects_per_lithoidx=3.0,
        max_objects_lithoidx={"lithoidx": 3, "lithoname": "현무암", "count": 4},
        max_area_lithoidx={"lithoidx": 2, "lithoname": "편마암", "total_area": 550.0},
        age_distribution={
            "신생대 제4기": 3,
            "중생대 백악기": 3,
            "선캄브리아시대": 2,
            "중생대 쥐라기": 1,
        },
        map_coverage={"서울", "대전", "강릉", "속초"},
    )


class TestPrintLithoidxInfo:
    """print_lithoidx_info 함수 테스트"""

    @patch("builtins.print")
    def test_print_lithoidx_info_all(self, mock_print, mock_analysis_df):
        """전체 정보 출력 테스트"""
        # When: 전체 정보 출력
        print_lithoidx_info(mock_analysis_df)

        # Then: 출력이 호출되었는지 확인
        assert mock_print.called

        # 주요 내용이 출력되었는지 확인
        output_str = str(mock_print.call_args_list)
        assert "Lithoidx별 암상 정보 분석" in output_str
        assert "전체 lithoidx 수: 3개" in output_str

    @patch("builtins.print")
    def test_print_lithoidx_info_top_n(self, mock_print, mock_analysis_df):
        """상위 N개만 출력 테스트"""
        # When: 상위 2개만 출력
        print_lithoidx_info(mock_analysis_df, top_n=2)

        # Then: 출력이 호출되었는지 확인
        assert mock_print.called

        # 상위 2개와 나머지 메시지가 출력되었는지 확인
        output_str = str(mock_print.call_args_list)
        assert "... 외 1개 lithoidx" in output_str


class TestPrintSummaryStatistics:
    """print_summary_statistics 함수 테스트"""

    @patch("builtins.print")
    def test_print_summary_statistics(self, mock_print, mock_lithoidx_stats):
        """통계 요약 출력 테스트"""
        # When: 통계 요약 출력
        print_summary_statistics(mock_lithoidx_stats)

        # Then: 주요 통계 정보가 출력되었는지 확인
        output_str = str(mock_print.call_args_list)
        assert "전체 통계 요약" in output_str
        assert "총 lithoidx 수: 3" in output_str
        assert "총 객체 수: 9" in output_str
        assert "가장 많은 객체를 가진 lithoidx" in output_str
        assert "가장 넓은 면적을 가진 lithoidx" in output_str


class TestSaveToCsv:
    """save_to_csv 함수 테스트"""

    @patch("builtins.print")
    def test_save_to_csv(self, mock_print, mock_analysis_df, tmp_path):
        """CSV 저장 테스트"""
        # Given: 출력 파일 경로
        output_path = tmp_path / "test_output.csv"

        # When: CSV 저장
        save_to_csv(mock_analysis_df, output_path)

        # Then: 파일이 생성되었는지 확인
        assert output_path.exists()

        # CSV 내용 확인
        df = pd.read_csv(output_path)
        assert len(df) == 3
        assert "lithoidx" in df.columns
        assert "lithoname" in df.columns

        # 저장 완료 메시지 출력 확인
        mock_print.assert_called_with(f"\nCSV 파일 저장 완료: {output_path}")


class TestHandleSearchMode:
    """handle_search_mode 함수 테스트"""

    @patch("src.main4_list_soil.soil_loader.search_lithoidx")
    @patch("src.main4_list_soil.print_lithoidx_info")
    def test_search_success(self, mock_print_info, mock_search, mock_analysis_df):
        """검색 성공 테스트"""
        # Given: 검색 결과가 있음
        search_result = mock_analysis_df.head(1)
        mock_search.return_value = search_result

        # When: 검색 실행
        with patch("builtins.print") as mock_print:
            handle_search_mode(mock_analysis_df, "화강")

        # Then: 검색 결과 출력
        mock_search.assert_called_once_with(mock_analysis_df, "화강")
        mock_print_info.assert_called_once_with(search_result)
        mock_print.assert_any_call("\n'화강' 검색 결과: 1개")

    @patch("src.main4_list_soil.soil_loader.search_lithoidx")
    def test_search_not_found(self, mock_search):
        """검색 결과 없음 테스트"""
        # Given: 검색 결과가 없음
        mock_search.return_value = pd.DataFrame()

        # When: 검색 실행
        with patch("builtins.print") as mock_print:
            handle_search_mode(pd.DataFrame(), "없는암석")

        # Then: 검색 실패 메시지 출력
        mock_print.assert_any_call("\n'없는암석'에 해당하는 결과를 찾을 수 없습니다.")


class TestMain:
    """main 함수 테스트"""

    @patch("src.main4_list_soil.soil_loader.load_soil_data")
    @patch("src.main4_list_soil.soil_loader.analyze_lithoidx")
    @patch("src.main4_list_soil.soil_loader.generate_lithoidx_statistics")
    @patch("src.main4_list_soil.print_lithoidx_info")
    @patch("src.main4_list_soil.print_summary_statistics")
    @patch("sys.argv", ["main4_list_soil.py"])
    def test_main_default(
        self,
        mock_print_summary,
        mock_print_info,
        mock_gen_stats,
        mock_analyze,
        mock_load_soil,
        mock_analysis_df,
        mock_lithoidx_stats,
    ):
        """기본 실행 테스트"""
        # Given: Mock 설정
        mock_gdf = MagicMock()
        mock_load_soil.return_value = mock_gdf
        mock_analyze.return_value = mock_analysis_df
        mock_gen_stats.return_value = mock_lithoidx_stats

        # When: main 함수 실행
        main()

        # Then: 함수 호출 확인
        mock_load_soil.assert_called_once()
        mock_analyze.assert_called_once_with(mock_gdf)
        mock_gen_stats.assert_called_once_with(mock_analysis_df)
        mock_print_info.assert_called_once_with(mock_analysis_df, None)
        mock_print_summary.assert_called_once_with(mock_lithoidx_stats)

    @patch("src.main4_list_soil.soil_loader.load_soil_data")
    @patch("src.main4_list_soil.soil_loader.analyze_lithoidx")
    @patch("src.main4_list_soil.handle_search_mode")
    @patch("sys.argv", ["main4_list_soil.py", "--search", "화강암"])
    def test_main_search(
        self, mock_handle_search, mock_analyze, mock_load_soil, mock_analysis_df
    ):
        """검색 모드 테스트"""
        # Given: Mock 설정
        mock_gdf = MagicMock()
        mock_load_soil.return_value = mock_gdf
        mock_analyze.return_value = mock_analysis_df

        # When: main 함수 실행
        main()

        # Then: 검색 모드 호출 확인
        mock_handle_search.assert_called_once_with(mock_analysis_df, "화강암")

    @patch("src.main4_list_soil.soil_loader.load_soil_data")
    @patch("src.main4_list_soil.soil_loader.analyze_lithoidx")
    @patch("src.main4_list_soil.soil_loader.generate_lithoidx_statistics")
    @patch("src.main4_list_soil.save_to_csv")
    @patch("src.main4_list_soil.print_lithoidx_info")
    @patch("src.main4_list_soil.print_summary_statistics")
    @patch("sys.argv", ["main4_list_soil.py", "--csv"])
    def test_main_csv_save(
        self,
        mock_print_summary,
        mock_print_info,
        mock_save,
        mock_gen_stats,
        mock_analyze,
        mock_load_soil,
        mock_analysis_df,
        mock_lithoidx_stats,
    ):
        """CSV 저장 모드 테스트"""
        # Given: Mock 설정
        mock_gdf = MagicMock()
        mock_load_soil.return_value = mock_gdf
        mock_analyze.return_value = mock_analysis_df
        mock_gen_stats.return_value = mock_lithoidx_stats

        # When: main 함수 실행
        main()

        # Then: CSV 저장 함수 호출 확인
        mock_save.assert_called_once()

    @patch("src.main4_list_soil.soil_loader.load_soil_data")
    @patch("sys.argv", ["main4_list_soil.py"])
    def test_main_no_data(self, mock_load_soil, capsys):
        """데이터가 없는 경우 테스트"""
        # Given: 데이터 로드 실패
        mock_load_soil.return_value = None

        # When: main 함수 실행
        main()

        # Then: 오류 메시지 출력
        captured = capsys.readouterr()
        assert "오류: Litho 데이터를 로드할 수 없습니다." in captured.out

    @patch("src.main4_list_soil.soil_loader.load_soil_data")
    @patch("src.main4_list_soil.soil_loader.analyze_lithoidx")
    @patch("src.main4_list_soil.soil_loader.generate_lithoidx_statistics")
    @patch("src.main4_list_soil.print_summary_statistics")
    @patch("sys.argv", ["main4_list_soil.py", "--summary"])
    def test_main_summary_only(
        self,
        mock_print_summary,
        mock_gen_stats,
        mock_analyze,
        mock_load_soil,
        mock_analysis_df,
        mock_lithoidx_stats,
    ):
        """요약만 출력 모드 테스트"""
        # Given: Mock 설정
        mock_gdf = MagicMock()
        mock_load_soil.return_value = mock_gdf
        mock_analyze.return_value = mock_analysis_df
        mock_gen_stats.return_value = mock_lithoidx_stats

        # When: main 함수 실행
        main()

        # Then: 요약만 출력되었는지 확인
        mock_print_summary.assert_called_once_with(mock_lithoidx_stats)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
