import java.util.*;

public class RunRamblersAstart {

    public static void main(String[] arg) {

        TerrainMap map = new TerrainMap("diablo.pgm");

        RamblersSearch searcher = new RamblersSearch(map, new Coords(7, 0));
        SearchState initState = (SearchState) new RamblersState(new Coords(5,8), 0, 0);

        String res_bb = searcher.runSearch(initState, "AStar");
        System.out.println(res_bb);
    }
}