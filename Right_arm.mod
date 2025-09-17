MODULE DrawingModule
    !==================================================
    ! ROBOT DRAWING SYSTEM
    ! Compatible with Python Robot Drawing System
    !==================================================
    
    ! Socket communication variables
    VAR socketdev client_socket;        ! Connection to Python client
    VAR socketdev server_socket;        ! Server socket listener
    VAR string received_string;         ! Buffer for incoming commands
    
    ! Z-axis positions for pen control
    CONST num z_down:=0;                ! Pen touching paper (drawing)
    CONST num z_up:=-10;                ! Pen lifted (moving)
    
    ! Batch coordinate processing - Enhanced for higher performance
    VAR robtarget batch_targets{15};    ! Buffer for batch coordinates (increased to 15 points)
    VAR num batch_count;                ! Number of coordinates in current batch
    VAR num max_batch_size := 30;       ! Increased maximum batch size for performance
     
    ! Position control variables 
    VAR robtarget retreat_position;
    VAR robtarget target_position;      ! Current target coordinates
    VAR num current_z;                  ! Current Z position (pen state)
    PERS wobjdata current_wobject;
    
    ! Movement parameters - optimized for smooth, precise drawing
    CONST speeddata move_speed := v1500;   
    CONST speeddata fast_speed := v1500;   
    CONST zonedata move_zone := z0;       
    CONST zonedata batch_zone := z0;       
    CONST num z_height := 0;               
    
    
    !==================================================
    ! WAIT FOR CLIENT - Safe connection waiting without RETRY
    !==================================================
    FUNC bool WaitForClient()
        SocketAccept server_socket, client_socket \Time:=10;  ! 10 second timeout
        RETURN TRUE;  ! Successfully accepted a client
        
        ERROR
            IF ERRNO = ERR_SOCK_TIMEOUT THEN
                RETURN FALSE;
            ELSE
                TPWrite "Socket error: " + NumToStr(ERRNO, 0) + " - continuing to wait";
                RETURN FALSE;
            ENDIF
    ENDFUNC
    
    !==================================================
    ! MAIN PROCEDURE - Server initialization and loop
    !==================================================
    PROC main()
        CornerPathWarning FALSE;
        MotionSup \Off;
        AccSet 100, 100;  
        ! Initialize robot to base position
        target_position:=base_position;
        !move_to_transit_position
        MoveJ start_traansition_r,fast_speed,move_zone, tool1 \WObj:=wobj0;
        ! Setup TCP server on port 1025 (matches Python client)
        SocketCreate server_socket;
        SocketBind server_socket, "0.0.0.0", 1025;
        SocketListen server_socket;
        TPWrite "Drawing server ready on port 1025";
        
        ! Main server loop - handles multiple client connections
        WHILE TRUE DO
            ! Try to accept a client connection
            IF WaitForClient() THEN
                TPWrite "Python client connected";
                
                ! Process drawing commands from client
                ProcessClientCommands;
                
                ! Cleanup after client disconnects
                SocketClose client_socket;
                TPWrite "Client disconnected";
            ELSE
                ! No client connected or error - just continue waiting
                WaitTime 1.0;
            ENDIF
        ENDWHILE
        
        SocketClose server_socket;
    ENDPROC
    !==================================================
    ! COMMAND PROCESSING - Main communication loop
    !==================================================
    PROC ProcessClientCommands()
        WHILE TRUE DO
            received_string := "";
            SocketReceive client_socket \Str:=received_string \Time:=40000;
            
            ! Process valid commands (ignore empty strings)
            IF StrLen(received_string) > 0 THEN
                ParseAndExecuteCommand received_string;
            ENDIF
        ENDWHILE
        ERROR
            IF ERRNO = ERR_SOCK_TIMEOUT THEN
                TPWrite "Client timeout - returning to wait for new client";
                SocketClose client_socket;
                RETURN;  ! Return to main loop to wait for new client
            ELSEIF ERRNO = ERR_SOCK_CLOSED THEN
                TPWrite "Socket closed by remote host, cleaning up";
                SocketClose client_socket;
                RETURN;
            ELSE
                TPWrite "Connection error: " + NumToStr(ERRNO, 0);
                TPWrite "Returning to wait for new client connection";
                SocketClose client_socket;
                RETURN; 
            ENDIF
        
    ENDPROC
    
    !==================================================
    ! COMMAND PARSER - Routes commands to handlers
    !==================================================
    PROC ParseAndExecuteCommand(string cmd)
        ! Clean input - remove line endings from Python
        cmd := StrMap(cmd, "\0A\0D", "");
        ! Route commands to appropriate handlers
        TEST cmd
        DEFAULT:
            IF StrMatch(cmd, 1, "STOP") = 1 THEN
                HandleStopCommand;
            ELSEIF StrMatch(cmd, 1, "MOVE,") = 1 THEN
                HandleMoveCommand cmd;
            ELSEIF StrMatch(cmd, 1, "BATCH,") = 1 THEN
                HandleBatchCommand cmd;
            ELSEIF StrMatch(cmd, 1, "PEN_UP") = 1 THEN
                current_z:=z_up; 
                MoveL Offs(target_position,0,0,current_z),fast_speed,move_zone,tool1 \WObj:=current_wobject;
                SendResponse("OK");
            ELSEIF StrMatch(cmd, 1, "PEN_DOWN") = 1 THEN
                current_z:=z_down;
                MoveL Offs(target_position,0,0,current_z),fast_speed,move_zone,tool1 \WObj:=current_wobject;
                SendResponse("OK");
            ELSEIF StrMatch(cmd, 1, "START") = 1 THEN
                setup_corner;
            ELSEIF StrMatch(cmd, 1, "START_CORNER") = 1 THEN 
                setup_corner;
            ELSEIF StrMatch(cmd, 1, "WAIT") = 1 THEN
                MoveL Offs(base_position,-20,0,current_z),fast_speed,move_zone,tool1 \WObj:=current_wobject;
                SendResponse("OK"); 
            ELSEIF StrMatch(cmd, 1, "RETREAT")=1 THEN
                retreat_position := Offs(target_position,-80,0,current_z);  ! Right arm retreats in negative X
                MoveL retreat_position,fast_speed,move_zone,tool1 \WObj:=current_wobject;
                
                ! Update target position to retreat position to avoid return movement
                target_position := retreat_position;

                SendResponse("OK");
            ELSE
                SendResponse("ERROR: Unknown command");
            ENDIF
        ENDTEST
        
    ERROR
        TPWrite "Command error: " ;
        SendResponse("ERROR: ");
    ENDPROC
    
    !==================================================
    ! BATCH MOVEMENT HANDLER - Processes BATCH,X1,Y1,X2,Y2,... commands
    !==================================================
    PROC HandleBatchCommand(string cmd)
        VAR num coord_count;        ! Number of coordinates parsed
        VAR num pos;               ! Current position in string
        VAR num next_pos;          ! Next comma position
        VAR string coord_str;      ! Current coordinate string
        VAR num coord_value;       ! Parsed coordinate value
        VAR num point_idx;         ! Current point index
        VAR num x_coord;           ! Current X coordinate
        VAR num y_coord;           ! Current Y coordinate
        
        ! Initialize parsing
        batch_count := 0;
        pos := 7;  ! Start after "BATCH,"
        coord_count := 0;
        
        ! Parse all coordinates in the batch - Enhanced for larger batches
        WHILE pos <= StrLen(cmd) AND batch_count < max_batch_size DO
            ! Find next comma or end of string
            next_pos := StrFind(cmd, pos, ",");
            IF next_pos = 0 THEN
                next_pos := StrLen(cmd) + 1;
            ENDIF
            
            ! Extract coordinate string
            coord_str := StrPart(cmd, pos, next_pos - pos);
            
            ! Convert to number
            IF StrToVal(coord_str, coord_value) THEN
                coord_count := coord_count + 1;
                
                ! Store coordinate (alternating X and Y)
                IF coord_count MOD 2 = 1 THEN
                    ! Odd count = X coordinate
                    x_coord := coord_value;
                ELSE
                    ! Even count = Y coordinate, complete the point
                    y_coord := coord_value;
                    
                    ! Store complete coordinate pair
                    batch_count := batch_count + 1;
                    batch_targets{batch_count} := offs(base_position, x_coord, y_coord, current_z);
                ENDIF
            ELSE
                SendResponse("ERROR: Invalid batch coordinate format");
                RETURN;
            ENDIF
            
            pos := next_pos + 1;
        ENDWHILE
        
        ! Validate we have complete coordinate pairs
        IF coord_count MOD 2 <> 0 THEN
            SendResponse("ERROR: Incomplete coordinate pairs in batch");
            RETURN;
        ENDIF
        
        ! Execute all moves in the batch with precise movement
        FOR point_idx FROM 1 TO batch_count DO
            target_position := batch_targets{point_idx};
            ! Use consistent smooth movement for all batch points to avoid corner stops
            MoveL target_position, fast_speed, move_zone, tool1 \WObj:=current_wobject ;
        ENDFOR
        
        SendResponse("OK");
        
    ERROR
        TPWrite "Batch command error";
        SendResponse("ERROR: Batch processing failed");
    ENDPROC
    
    !==================================================
    ! MOVEMENT HANDLER - Processes MOVE,X,Y commands
    !==================================================
    PROC HandleMoveCommand(string cmd)
        VAR num x_coord;    ! Parsed X coordinate (mm)
        VAR num y_coord;    ! Parsed Y coordinate (mm)
        VAR num pos1;       ! First comma position
        VAR num pos2;       ! Second comma position
        
        ! Parse command format: "MOVE,X,Y"
        pos1 := StrFind(cmd, 1, ",");
        pos2 := StrFind(cmd, pos1 + 1, ",");
        
        ! Validate command structure
        IF pos1 = 0 OR pos2 = 0 THEN
            SendResponse("ERROR: Format should be MOVE,X,Y");
            RETURN;
        ENDIF
        
        ! Extract and validate numeric coordinates
        IF NOT(StrToVal(StrPart(cmd, pos1 + 1, pos2 - pos1 - 1), x_coord) AND
               StrToVal(StrPart(cmd, pos2 + 1, StrLen(cmd) - pos2), y_coord)) THEN
            SendResponse("ERROR: Invalid coordinates");
            RETURN;
        ENDIF
        
        
        ! Execute movement relative to base_position with precise movement
        target_position := offs(base_position, x_coord, y_coord, current_z);
        MoveL target_position, fast_speed, move_zone, tool1 \WObj:=current_wobject;
        
        SendResponse("OK");
    ENDPROC
    
    !==================================================
    ! STOP - Returns robot to safe position
    !==================================================
    PROC HandleStopCommand()
        TPWrite "Stop command received";
        ! Return to base position safely with smooth movement
        target_position := base_position;
        MoveL Offs(target_position, 0, 0, current_z), fast_speed, move_zone, tool1 \WObj:=current_wobject;
        SendResponse("STOPPED");
    ENDPROC
    
    !==================================================
    ! RESPONSE SENDER - Sends status back to Python
    !==================================================
    PROC SendResponse(string msg)
        ! Send the response and terminate with CRLF so the Python client can read a full line (OK\r\n)
        SocketSend client_socket \Str:=msg;
        ! Send CRLF separately to avoid relying on string concatenation semantics
        SocketSend client_socket \Str:="\0D\0A";
    ENDPROC
    
    PROC setup_corner()
        current_wobject:=const_kartka;
        current_z:=z_up;
        base_position:=  [[20.53,14.09,95.81],[0.0236703,-0.671026,0.0261252,-0.740595],[1,0,-2,4],[159.113,9E+09,9E+09,9E+09,9E+09,9E+09]];
        MoveJ Offs(base_position,0,0,-10),fast_speed,fine,tool1\WObj:=current_wobject;
        SendResponse("OK");
    ENDPROC
ENDMODULE