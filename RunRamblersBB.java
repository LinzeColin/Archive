import java.util.*;

public class RunRamblersBB {

    public static void main(String[] arg) {

        TerrainMap map = new TerrainMap("diablo.pgm");

        RamblersSearch searcher = new RamblersSearch(map, new Coords(5, 8));
        SearchState initState = (SearchState) new RamblersState(new Coords(7,0), 0, 0);

        String res_bb = searcher.runSearch(initState, "branchAndBound");
        System.out.println(res_bb);
    }
}